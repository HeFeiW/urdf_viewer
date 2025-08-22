from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch.conditions import IfCondition
import os
from ament_index_python.packages import get_package_share_directory
def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot',
            default_value='panda',
            description='Robot type: panda, leaphand, dexhand'
        ),
        DeclareLaunchArgument(
            'gui',
            default_value='True',
            description='Flag to enable joint_state_publisher GUI'
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            condition=IfCondition(LaunchConfiguration('gui'))
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            arguments=[
                PathJoinSubstitution([
                    '/workspace/RDF_ori/show_urdf/src/show_urdf',
                    LaunchConfiguration('robot')
                    # 这里假设你的urdf文件名和robot参数一致，比如leaphand -> leap_hand_left.urdf
                    # 如果不一致，可以用一个映射shell脚本或提前处理
                ])
            ]
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        )
    ])