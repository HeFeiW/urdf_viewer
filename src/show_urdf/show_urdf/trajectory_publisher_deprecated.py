import json
import os
from typing import Dict, List, Tuple, Union

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from ament_index_python.packages import get_package_share_directory


PANDA_ARM_JOINTS = [
    'panda_joint1',
    'panda_joint2',
    'panda_joint3',
    'panda_joint4',
    'panda_joint5',
    'panda_joint6',
    'panda_joint7',
]
PANDA_GRIPPER_JOINTS = ['panda_finger_joint1']
PANDA_BASE_JOINTS = [
    'panda_base_x',
    'panda_base_y',
    'panda_base_z',
    'panda_base_roll',
    'panda_base_pitch',
    'panda_base_yaw',
]
PANDA_MIMIC_JOINTS = {
    'panda_finger_joint2': 'panda_finger_joint1'
}


class TrajectoryPublisher(Node):
    def __init__(self):
        super().__init__('trajectory_publisher')
        self.declare_parameter('trajectory_file', 'trajectory.json')
        self.declare_parameter('robot_model', 'panda_with_base')
        self.declare_parameter('frame_id', 'world')
        self.declare_parameter('loop', True)
        self.declare_parameter('joint_names', [])

        self.publisher = self.create_publisher(JointState, '/joint_states', 10)
        self._timer = None
        self._trajectory = []
        self._trajectory_index = 0

        self._load_trajectory()
        self.get_logger().info(f'initial transform:\n{self._trajectory[0]}')
        if not self._trajectory:
            self.get_logger().error('No trajectory loaded; publisher will remain idle.')
            return

        self._schedule_next()

    def _resolve_path(self, path_value: str) -> str:
        if os.path.isabs(path_value) and os.path.exists(path_value):
            return path_value

        if os.path.exists(path_value):
            return os.path.abspath(path_value)

        try:
            package_share = get_package_share_directory('show_urdf')
        except Exception:
            package_share = None

        if package_share:
            candidate = os.path.join(package_share, path_value)
            if os.path.exists(candidate):
                return candidate

            candidate = os.path.join(package_share, os.path.basename(path_value))
            if os.path.exists(candidate):
                return candidate

        return path_value

    def _load_trajectory(self) -> None:
        trajectory_file = self.get_parameter('trajectory_file').get_parameter_value().string_value
        resolved_path = self._resolve_path(trajectory_file)

        if not os.path.exists(resolved_path):
            self.get_logger().error(f'Trajectory file not found: {resolved_path}')
            return

        with open(resolved_path, 'r', encoding='utf-8') as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                self.get_logger().error(f'Failed to parse JSON: {exc}')
                return

        trajectory = data.get('trajectory') if isinstance(data, dict) else None
        if not trajectory:
            self.get_logger().error('Trajectory JSON missing "trajectory" list.')
            return

        self._trajectory = trajectory
        self._joint_names = self._resolve_joint_names(data)
        self._mimic_map = self._resolve_mimic_map(data)

        self.get_logger().info(
            f'Loaded trajectory with {len(self._trajectory)} steps and '
            f'{len(self._joint_names)} joints.'
        )

    def _resolve_joint_names(self, data: Dict) -> List[str]:
        joint_names_param = self.get_parameter('joint_names').get_parameter_value().string_array_value
        if joint_names_param:
            return list(joint_names_param)

        if isinstance(data, dict):
            json_joint_names = data.get('joint_names')
            if isinstance(json_joint_names, list) and json_joint_names:
                return [str(name) for name in json_joint_names]

        robot_model = self.get_parameter('robot_model').get_parameter_value().string_value
        if isinstance(data, dict) and data.get('robot_model'):
            robot_model = data.get('robot_model')

        if robot_model == 'panda_with_base':
            return PANDA_BASE_JOINTS + PANDA_ARM_JOINTS + PANDA_GRIPPER_JOINTS
        if robot_model == 'panda':
            return PANDA_ARM_JOINTS + PANDA_GRIPPER_JOINTS

        return []

    def _resolve_mimic_map(self, data: Dict) -> Dict[str, str]:
        robot_model = self.get_parameter('robot_model').get_parameter_value().string_value
        if isinstance(data, dict) and data.get('robot_model'):
            robot_model = data.get('robot_model')

        if robot_model in ('panda', 'panda_with_base'):
            return PANDA_MIMIC_JOINTS
        return {}

    def _schedule_next(self) -> None:
        if self._trajectory_index >= len(self._trajectory):
            if self.get_parameter('loop').get_parameter_value().bool_value:
                self._trajectory_index = 0
            else:
                self.get_logger().info('Trajectory playback finished.')
                return

        step = self._trajectory[self._trajectory_index]
        interval = float(step.get('time_interval', 0.01))
        if interval <= 0.0:
            interval = 0.01

        if self._timer is not None:
            self._timer.cancel()

        self._timer = self.create_timer(interval, self._publish_step)

    def _publish_step(self) -> None:
        if self._timer is not None:
            self._timer.cancel()

        if self._trajectory_index >= len(self._trajectory):
            return

        step = self._trajectory[self._trajectory_index]
        joints = step.get('joints', [])
        if not isinstance(joints, (list, dict)):
            self.get_logger().warning('Invalid joints format; skipping step.')
            self._trajectory_index += 1
            self._schedule_next()
            return

        names, positions = self._build_joint_state(joints)
        if not names:
            self.get_logger().warning('Joint name list is empty; skipping step.')
            self._trajectory_index += 1
            self._schedule_next()
            return

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        msg.name = names
        msg.position = positions
        msg.velocity = []
        msg.effort = []
        self.publisher.publish(msg)

        self._trajectory_index += 1
        self._schedule_next()

    def _build_joint_state(self, joints: Union[List[float], Dict[str, float]]) -> Tuple[List[str], List[float]]:
        if isinstance(joints, dict):
            return self._build_joint_state_from_mapping(joints)

        base_names = list(self._joint_names)
        if not base_names:
            base_names = [f'joint_{idx + 1}' for idx in range(len(joints))]

        if len(joints) != len(base_names):
            if len(joints) < len(base_names):
                self.get_logger().warning(
                    f'Joint count mismatch: expected {len(base_names)}, got {len(joints)}.'
                )
                base_names = base_names[:len(joints)]
            else:
                self.get_logger().warning(
                    f'Joint count mismatch: expected {len(base_names)}, got {len(joints)}.'
                )
                base_names = base_names + [
                    f'joint_{idx + 1}' for idx in range(len(base_names), len(joints))
                ]

        names = list(base_names)
        positions = [float(value) for value in joints]

        return self._append_mimic_joints(names, positions)

    def _build_joint_state_from_mapping(self, joints: Dict[str, float]) -> Tuple[List[str], List[float]]:
        if self._joint_names:
            names = list(self._joint_names)
        else:
            names = list(joints.keys())

        positions: List[float] = []
        for name in names:
            if name in joints:
                positions.append(float(joints[name]))
            else:
                self.get_logger().warning(
                    f'Joint "{name}" missing in mapping; defaulting to 0.0.'
                )
                positions.append(0.0)

        for name, value in joints.items():
            if name not in names:
                names.append(name)
                positions.append(float(value))

        return self._append_mimic_joints(names, positions)

    def _append_mimic_joints(self, names: List[str], positions: List[float]) -> Tuple[List[str], List[float]]:
        if self._mimic_map:
            for mimic_joint, source_joint in self._mimic_map.items():
                if mimic_joint in names:
                    continue
                if source_joint in names:
                    source_index = names.index(source_joint)
                    names.append(mimic_joint)
                    positions.append(positions[source_index])

        return names, positions


def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
