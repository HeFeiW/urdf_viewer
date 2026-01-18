#!/usr/bin/env python3
"""
轨迹文件生成工具

这个脚本展示如何以编程方式生成轨迹JSON文件。
可以根据需要修改轨迹生成逻辑。
"""

import json
import math
from typing import List, Dict, Any

def generate_sinusoidal_trajectory() -> Dict[str, Any]:
    """生成正弦波轨迹"""
    trajectory = []
    time_interval = 0.01
    
    # 时间步数（10秒，10Hz）
    num_steps = 1000
    
    for i in range(num_steps):
        t = i * time_interval
        
        # 6个base自由度的正弦波轨迹
        base_x = 0.5 * math.sin(t)           # X轴平移
        base_y = 0.3 * math.cos(t)           # Y轴平移
        base_z = 0.1 + 0.05 * math.sin(2*t) # Z轴平移
        base_roll = 0.1 * math.sin(t)        # 翻滚
        base_pitch = 0.1 * math.cos(t)       # 俯仰
        base_yaw = t * 0.5                   # 偏航
        
        # 机械臂关节（预设位置）
        arm_j1 = 0.0
        arm_j2 = -0.5
        arm_j3 = 0.0
        arm_j4 = -1.5
        arm_j5 = 0.0
        arm_j6 = 0.0
        arm_j7 = 0.0
        gripper = 0.02 * math.sin(t)  # 夹爪开闭
        
        point = {
            "time_interval": time_interval,
            "joints": [
                base_x, base_y, base_z, base_roll, base_pitch, base_yaw,
                arm_j1, arm_j2, arm_j3, arm_j4, arm_j5, arm_j6, arm_j7,
                gripper
            ]
        }
        trajectory.append(point)
    
    return {
        "description": "正弦波基座运动轨迹 (Sinusoidal base motion)",
        "robot_model": "panda_with_base",
        "trajectory": trajectory
    }

def generate_circular_motion() -> Dict[str, Any]:
    """生成圆周运动轨迹"""
    trajectory = []
    time_interval = 0.01
    num_steps = 1000
    
    radius = 0.3
    angular_velocity = 1.0  # rad/s
    
    for i in range(num_steps):
        t = i * time_interval
        theta = angular_velocity * t
        
        # 圆周运动
        base_x = radius * math.cos(theta)
        base_y = radius * math.sin(theta)
        base_z = 0.0
        base_roll = 0.0
        base_pitch = 0.0
        base_yaw = theta  # 跟随圆周方向
        
        # 机械臂保持固定
        arm_joints = [0.0, -0.5, 0.0, -1.5, 0.0, 0.0, 0.0, 0.02]
        
        point = {
            "time_interval": time_interval,
            "joints": [base_x, base_y, base_z, base_roll, base_pitch, base_yaw] + arm_joints
        }
        trajectory.append(point)
    
    return {
        "description": "圆周运动轨迹 (Circular motion)",
        "robot_model": "panda_with_base",
        "trajectory": trajectory
    }

def generate_reach_and_grasp() -> Dict[str, Any]:
    """生成伸手并抓取的轨迹"""
    trajectory = []
    time_interval = 0.01
    duration = 5.0  # 5秒轨迹
    num_steps = int(duration / time_interval)
    
    for i in range(num_steps):
        t = i * time_interval
        
        # Base保持不动
        base = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        
        # 分段轨迹
        if t < 1.0:  # 0-1秒：初始姿态
            arm = [0.0, -0.5, 0.0, -1.5, 0.0, 0.0, 0.0]
            gripper = 0.04  # 打开
        elif t < 2.0:  # 1-2秒：移动到目标上方
            progress = (t - 1.0) / 1.0
            arm = [
                0.5 * progress,
                -0.5 - 0.3 * progress,
                0.0 + 0.2 * progress,
                -1.5 - 0.2 * progress,
                0.0,
                0.0,
                0.0
            ]
            gripper = 0.04
        elif t < 3.0:  # 2-3秒：向下移动以抓取
            progress = (t - 2.0) / 1.0
            arm = [
                0.5,
                -0.8,
                0.2 - 0.15 * progress,
                -1.7 - 0.1 * progress,
                0.0,
                0.0,
                0.0
            ]
            gripper = 0.04
        elif t < 4.0:  # 3-4秒：关闭夹爪并提起
            progress = (t - 3.0) / 1.0
            arm = [
                0.5,
                -0.8,
                0.05 + 0.15 * progress,
                -1.8 + 0.1 * progress,
                0.0,
                0.0,
                0.0
            ]
            gripper = 0.04 - 0.04 * progress  # 关闭
        else:  # 4-5秒：回到初始位置
            progress = (t - 4.0) / 1.0
            arm = [
                0.5 * (1 - progress),
                -0.5 - 0.3 * (1 - progress),
                0.2 * (1 - progress),
                -1.7 - 0.2 * (1 - progress),
                0.0,
                0.0,
                0.0
            ]
            gripper = 0.0
        
        point = {
            "time_interval": time_interval,
            "joints": base + arm + [gripper]
        }
        trajectory.append(point)
    
    return {
        "description": "伸手抓取物体轨迹 (Reach and grasp)",
        "robot_model": "panda_with_base",
        "trajectory": trajectory
    }

def save_trajectory(trajectory_dict: Dict[str, Any], filename: str):
    """保存轨迹到JSON文件"""
    with open(filename, 'w') as f:
        json.dump(trajectory_dict, f, indent=2)
    print(f"✓ 轨迹已保存到: {filename} ({len(trajectory_dict['trajectory'])} 个点)")

if __name__ == '__main__':
    # 生成并保存多种轨迹
    
    # 1. 正弦波轨迹
    print("生成正弦波轨迹...")
    sinusoidal = generate_sinusoidal_trajectory()
    save_trajectory(sinusoidal, 'trajectory_sinusoidal.json')
    
    # 2. 圆周运动
    print("生成圆周运动轨迹...")
    circular = generate_circular_motion()
    save_trajectory(circular, 'trajectory_circular.json')
    
    # 3. 伸手抓取
    print("生成伸手抓取轨迹...")
    reach = generate_reach_and_grasp()
    save_trajectory(reach, 'trajectory_reach_grasp.json')
    
    print("\n所有轨迹文件已生成！")
    print("\n使用方法:")
    print("ros2 launch show_urdf trajectory_launch.py trajectory_file:=trajectory_sinusoidal.json")
    print("ros2 launch show_urdf trajectory_launch.py trajectory_file:=trajectory_circular.json")
    print("ros2 launch show_urdf trajectory_launch.py trajectory_file:=trajectory_reach_grasp.json")
