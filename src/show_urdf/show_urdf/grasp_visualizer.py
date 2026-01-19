#!/usr/bin/env python3
"""
在RViz中可视化抓取
"""

import json
import argparse
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster
from scipy.spatial.transform import Rotation
import time


class GraspVisualizer(Node):
    def __init__(self):
        super().__init__('grasp_visualizer')
        self.declare_parameter('grasp_file', 'grasp.json')
        self.declare_parameter('scene_file', 'scene_config.json')
        grasp_file = self.get_parameter('grasp_file').get_parameter_value().string_value
        scene_file = self.get_parameter('scene_file').get_parameter_value().string_value
        # 加载抓取数据
        with open(grasp_file, 'r') as f:
            self.grasp_data = json.load(f)
        
        # 加载场景数据（如果提供）
        self.scene_data = None
        if scene_file:
            with open(scene_file, 'r') as f:
                self.scene_data = json.load(f)
        
        self.robot_name = self.grasp_data.get('robot_name', 'leap')
        
        # 创建发布器
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.tf_broadcaster = StaticTransformBroadcaster(self)
        
        # 发布手基座的TF
        self._publish_hand_base_tf()
        
        # 定时发布关节状态
        self.timer = self.create_timer(0.1, self._publish_joint_states)
        
        self.get_logger().info(f'开始可视化抓取 (机器人: {self.robot_name})')
    
    def _publish_hand_base_tf(self):
        """发布手基座的静态TF（从4x4变换矩阵）"""
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world'
        t.child_frame_id = 'palm_base'
        
        # 从4x4变换矩阵提取位置和姿态
        hand_pose = np.array(self.grasp_data['hand_base_transform'])  # 4x4矩阵
        
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
        self.get_logger().info(f'发布手基座TF: position={hand_pose[:3, 3]}')
    
    def _publish_joint_states(self):
        """发布关节状态"""
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'palm_base'
        
        # 获取关节位置
        joint_positions = self.grasp_data['joint_angles']
        
        # 根据机器人类型获取关节名称
        joint_names = self._get_joint_names(self.robot_name, len(joint_positions))
        
        msg.name = joint_names
        msg.position = joint_positions
        
        self.joint_pub.publish(msg)
    
    def _get_joint_names(self, robot_name, n_joints):
        """获取机器人关节名称"""
        if robot_name == 'allegro':
            # Allegro手有16个关节
            joint_names = []
            for i in range(4):  # 4个手指
                for j in range(4):  # 每个手指4个关节
                    joint_names.append(f'joint_{i}_{j}')
            return joint_names[:n_joints]
        
        elif robot_name == 'leap':
            # Leap手有16个关节
            joint_names = []
            for i in range(16):
                joint_names.append(f'joint_{i}')
            return joint_names[:n_joints]
        
        elif robot_name == 'shadow':
            # Shadow手的关节名称
            joint_names = [
                'rh_WRJ2', 'rh_WRJ1',
                'rh_FFJ4', 'rh_FFJ3', 'rh_FFJ2', 'rh_FFJ1',
                'rh_MFJ4', 'rh_MFJ3', 'rh_MFJ2', 'rh_MFJ1',
                'rh_RFJ4', 'rh_RFJ3', 'rh_RFJ2', 'rh_RFJ1',
                'rh_LFJ5', 'rh_LFJ4', 'rh_LFJ3', 'rh_LFJ2', 'rh_LFJ1',
                'rh_THJ5', 'rh_THJ4', 'rh_THJ3', 'rh_THJ2', 'rh_THJ1'
            ]
            return joint_names[:n_joints]
        
        elif robot_name == 'dclaw':
            # DClaw夹爪有9个关节
            return [f'joint_{i}' for i in range(n_joints)]
        
        else:
            # 默认命名
            return [f'joint_{i}' for i in range(n_joints)]


def main(args=None):
    rclpy.init(args=args)
    node = GraspVisualizer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
