#!/usr/bin/env python3
"""
在RViz中可视化抓取轨迹
"""

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
from scipy.spatial.transform import Rotation


class TrajectoryVisualizer(Node):
    def __init__(self):
        super().__init__('traj_visualizer')
        
        # 声明参数
        self.declare_parameter('trajectory_file', 'trajectory_demo.npz')
        self.declare_parameter('playback_speed', 1.0)
        self.declare_parameter('loop', True)
        
        # 获取参数
        trajectory_file = self.get_parameter('trajectory_file').get_parameter_value().string_value
        self.playback_speed = self.get_parameter('playback_speed').get_parameter_value().double_value
        self.loop = self.get_parameter('loop').get_parameter_value().bool_value
        
        # 加载轨迹数据
        try:
            data = np.load(trajectory_file)
            self.q_trajectory = data['q_trajectory']  # [n_steps, n_dof]
            self.transform_trajectory = data['transform_trajectory']  # [n_steps, 4, 4]
            self.timestamps = data['timestamps']  # [n_steps]
            
            self.get_logger().info(f'成功加载轨迹: {trajectory_file}')
            self.get_logger().info(f'  轨迹点数: {len(self.timestamps)}')
            self.get_logger().info(f'  时间范围: {self.timestamps[0]:.3f}s - {self.timestamps[-1]:.3f}s')
            self.get_logger().info(f'  关节自由度: {self.q_trajectory.shape[1]}')
            self.get_logger().info(f'  播放速度: {self.playback_speed}x')
            self.get_logger().info(f'  循环播放: {self.loop}')
            
        except Exception as e:
            self.get_logger().error(f'加载轨迹文件失败: {e}')
            raise
        
        # 创建发布器
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 轨迹播放状态
        self.current_index = 0
        self.n_steps = len(self.timestamps)
        
        # 计算更新频率（基于轨迹的时间间隔和播放速度）
        if self.n_steps > 1:
            avg_dt = (self.timestamps[-1] - self.timestamps[0]) / (self.n_steps - 1)
            update_rate = (1.0 / avg_dt) * self.playback_speed
        else:
            update_rate = 10.0  # 默认10Hz
        
        self.get_logger().info(f'更新频率: {update_rate:.1f}Hz')
        
        # 创建定时器
        self.timer = self.create_timer(1.0 / update_rate, self._update_trajectory)
        
    def _update_trajectory(self):
        """更新轨迹状态"""
        if self.current_index >= self.n_steps:
            if self.loop:
                self.current_index = 0
                self.get_logger().info('轨迹循环播放')
            else:
                self.get_logger().info('轨迹播放完成')
                self.timer.cancel()
                return
        
        # 发布当前时刻的关节状态和TF
        self._publish_joint_states(self.current_index)
        self._publish_hand_base_tf(self.current_index)
        
        # 进度信息（每10%输出一次）
        progress = (self.current_index / self.n_steps) * 100
        if self.current_index % max(1, self.n_steps // 10) == 0:
            self.get_logger().info(
                f'播放进度: {progress:.1f}% '
                f'(步数: {self.current_index}/{self.n_steps}, '
                f'时间: {self.timestamps[self.current_index]:.3f}s)'
            )
        
        self.current_index += 1
    
    def _publish_hand_base_tf(self, index):
        """发布手基座的TF"""
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world'
        t.child_frame_id = 'palm_base'
        
        # 从4x4变换矩阵提取位置和姿态
        hand_pose = self.transform_trajectory[index]
        
        # 位置
        t.transform.translation.x = float(hand_pose[0, 3])
        t.transform.translation.y = float(hand_pose[1, 3])
        t.transform.translation.z = float(hand_pose[2, 3])
        
        # 姿态 (从旋转矩阵转换为四元数)
        rotation_matrix = hand_pose[:3, :3]
        r = Rotation.from_matrix(rotation_matrix)
        quat = r.as_quat()  # [x, y, z, w]
        t.transform.rotation.x = float(quat[0])
        t.transform.rotation.y = float(quat[1])
        t.transform.rotation.z = float(quat[2])
        t.transform.rotation.w = float(quat[3])
        
        self.tf_broadcaster.sendTransform(t)
    
    def _publish_joint_states(self, index):
        """发布关节状态"""
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'palm_base'
        
        # 获取关节位置
        joint_positions = self.q_trajectory[index].tolist()
        n_joints = len(joint_positions)
        
        # 生成关节名称
        joint_names = self._get_joint_names(n_joints)
        
        msg.name = joint_names
        msg.position = joint_positions
        
        self.joint_pub.publish(msg)
    
    def _get_joint_names(self, n_joints):
        """获取机器人关节名称"""
        # 默认使用通用命名
        # 可以根据URDF或配置文件定制
        return [f'joint_{i}' for i in range(n_joints)]


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = TrajectoryVisualizer()
        rclpy.spin(node)
    except Exception as e:
        print(f'Error: {e}')
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
