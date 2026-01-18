import json
import math
import os
from typing import Dict, List

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray
from ament_index_python.packages import get_package_share_directory


class ScenePublisher(Node):
    def __init__(self):
        super().__init__('scene_publisher')
        self.declare_parameter('scene_config', 'scene_config.json')
        self.declare_parameter('publish_rate', 1.0)

        qos_profile = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher = self.create_publisher(MarkerArray, '/visualization_marker_array', qos_profile)

        self._scene = self._load_scene()
        if not self._scene:
            self.get_logger().error('No scene objects loaded; publisher will remain idle.')
            return

        if isinstance(self._scene, dict):
            self._default_frame_id = self._scene.get('frame_id', 'world')
        else:
            self._default_frame_id = 'world'

        self._marker_array = self._build_marker_array(self._scene)
        self._publish_scene()

        publish_rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        if publish_rate and publish_rate > 0.0:
            self.create_timer(1.0 / publish_rate, self._publish_scene)

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

    def _load_scene(self) -> Dict:
        scene_config = self.get_parameter('scene_config').get_parameter_value().string_value
        resolved_path = self._resolve_path(scene_config)
        if not os.path.exists(resolved_path):
            self.get_logger().error(f'Scene config not found: {resolved_path}')
            return {}

        with open(resolved_path, 'r', encoding='utf-8') as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                self.get_logger().error(f'Failed to parse JSON: {exc}')
                return {}

        return data

    def _build_marker_array(self, scene_data: Dict) -> MarkerArray:
        marker_array = MarkerArray()
        objects = scene_data.get('objects', []) if isinstance(scene_data, dict) else []

        for idx, obj in enumerate(objects):
            marker = self._create_marker_from_object(obj, idx)
            if marker is not None:
                marker_array.markers.append(marker)

        self.get_logger().info(f'Loaded scene with {len(marker_array.markers)} objects.')
        return marker_array

    def _publish_scene(self) -> None:
        if self._marker_array:
            self.publisher.publish(self._marker_array)

    def _create_marker_from_object(self, obj: Dict, marker_id: int) -> Marker:
        marker = Marker()
        marker.id = marker_id
        marker.ns = obj.get('name', 'scene')
        marker.action = Marker.ADD

        obj_type = obj.get('type', 'box').lower()
        if obj_type in ('box', 'cube'):
            marker.type = Marker.CUBE
        elif obj_type == 'sphere':
            marker.type = Marker.SPHERE
        elif obj_type == 'cylinder':
            marker.type = Marker.CYLINDER
        else:
            self.get_logger().warning(f'Unsupported object type: {obj_type}')
            return None

        frame_id = obj.get('frame_id') or obj.get('frame') or self._default_frame_id
        marker.header.frame_id = frame_id
        marker.header.stamp = self.get_clock().now().to_msg()

        position = obj.get('position', [0.0, 0.0, 0.0])
        orientation = obj.get('orientation', [0.0, 0.0, 0.0])
        scale = obj.get('scale', [0.1, 0.1, 0.1])
        color = obj.get('color', [0.5, 0.5, 0.5, 1.0])

        marker.pose.position.x = float(position[0]) if len(position) > 0 else 0.0
        marker.pose.position.y = float(position[1]) if len(position) > 1 else 0.0
        marker.pose.position.z = float(position[2]) if len(position) > 2 else 0.0

        quaternion = rpy_to_quaternion(
            float(orientation[0]) if len(orientation) > 0 else 0.0,
            float(orientation[1]) if len(orientation) > 1 else 0.0,
            float(orientation[2]) if len(orientation) > 2 else 0.0,
        )
        marker.pose.orientation.x = quaternion[0]
        marker.pose.orientation.y = quaternion[1]
        marker.pose.orientation.z = quaternion[2]
        marker.pose.orientation.w = quaternion[3]

        marker.scale.x = float(scale[0]) if len(scale) > 0 else 0.1
        marker.scale.y = float(scale[1]) if len(scale) > 1 else marker.scale.x
        marker.scale.z = float(scale[2]) if len(scale) > 2 else marker.scale.x

        marker.color.r = float(color[0]) if len(color) > 0 else 0.5
        marker.color.g = float(color[1]) if len(color) > 1 else 0.5
        marker.color.b = float(color[2]) if len(color) > 2 else 0.5
        marker.color.a = float(color[3]) if len(color) > 3 else 1.0

        marker.lifetime.sec = 0
        marker.lifetime.nanosec = 0
        return marker


def rpy_to_quaternion(roll: float, pitch: float, yaw: float) -> List[float]:
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy

    return [qx, qy, qz, qw]


def main(args=None):
    rclpy.init(args=args)
    node = ScenePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
