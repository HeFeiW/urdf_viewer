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
            'urdf',
            default_value='panda_with_base.urdf',
            description='URDF file within the show_urdf package'
        ),
        DeclareLaunchArgument(
            'robot_model',
            default_value='panda_with_base',
            description='Robot model identifier for joint ordering'
        ),
        DeclareLaunchArgument(
            'trajectory_file',
            default_value='trajectory.json',
            description='Trajectory JSON file'
        ),
        DeclareLaunchArgument(
            'scene_config',
            default_value='scene_config.json',
            description='Scene configuration JSON file'
        ),
        DeclareLaunchArgument(
            'with_scene',
            default_value='True',
            description='Whether to publish static scene objects'
        ),
        DeclareLaunchArgument(
            'with_rviz',
            default_value='True',
            description='Whether to launch RViz'
        ),
        DeclareLaunchArgument(
            'loop',
            default_value='True',
            description='Loop trajectory playback'
        ),
        DeclareLaunchArgument(
            'frame_id',
            default_value='world',
            description='Frame id for joint states'
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=PathJoinSubstitution([package_share, 'rviz', 'show_urdf.rviz']),
            description='RViz config file'
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            arguments=[
                PathJoinSubstitution([
                    package_share,
                    LaunchConfiguration('urdf')
                ])
            ]
        ),
        Node(
            package='show_urdf',
            executable='trajectory_publisher',
            name='trajectory_publisher',
            parameters=[{
                'trajectory_file': LaunchConfiguration('trajectory_file'),
                'robot_model': LaunchConfiguration('robot_model'),
                'frame_id': LaunchConfiguration('frame_id'),
                'loop': LaunchConfiguration('loop')
            }]
        ),
        Node(
            package='show_urdf',
            executable='scene_publisher',
            name='scene_publisher',
            parameters=[{
                'scene_config': LaunchConfiguration('scene_config')
            }],
            condition=IfCondition(LaunchConfiguration('with_scene'))
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(LaunchConfiguration('with_rviz')),
            arguments=['-d', LaunchConfiguration('rviz_config')]
        )
    ])
