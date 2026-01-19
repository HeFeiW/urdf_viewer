from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_share = get_package_share_directory('show_urdf')

    return LaunchDescription([
        DeclareLaunchArgument(
            'scene_config',
            default_value='scene_config.json',
            description='Scene configuration JSON file'
        ),
        DeclareLaunchArgument(
            'trajectory_file',
            default_value='trajectory_demo.npz',
            description='Trajectory data NPZ file'
        ),
        DeclareLaunchArgument(
            'robot_urdf',
            default_value='leaphand.urdf',
            description='Robot URDF file for the hand'
        ),
        DeclareLaunchArgument(
            'with_rviz',
            default_value='True',
            description='Whether to launch RViz'
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=PathJoinSubstitution([package_share, 'rviz', 'show_urdf.rviz']),
            description='RViz config file'
        ),
        DeclareLaunchArgument(
            'playback_speed',
            default_value='1.0',
            description='Trajectory playback speed multiplier'
        ),
        DeclareLaunchArgument(
            'loop',
            default_value='True',
            description='Whether to loop the trajectory'
        ),
        
        # 发布机器人模型（手）
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='hand_robot_state_publisher',
            arguments=[
                PathJoinSubstitution([
                    package_share,
                    LaunchConfiguration('robot_urdf')
                ])
            ]
        ),
        
        # 发布场景物体
        Node(
            package='show_urdf',
            executable='scene_publisher',
            name='scene_publisher',
            parameters=[{
                'scene_config': PathJoinSubstitution([
                    package_share,
                    'config',
                    LaunchConfiguration('scene_config')
                ])
            }]
        ),
        
        # 发布轨迹可视化
        Node(
            package='show_urdf',
            executable='traj_visualizer',
            name='traj_visualizer',
            parameters=[{
                'trajectory_file': PathJoinSubstitution([
                    package_share,
                    'config',
                    LaunchConfiguration('trajectory_file')
                ]),
                'playback_speed': LaunchConfiguration('playback_speed'),
                'loop': LaunchConfiguration('loop')
            }]
        ),
        
        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(LaunchConfiguration('with_rviz')),
            arguments=['-d', LaunchConfiguration('rviz_config')]
        )
    ])
