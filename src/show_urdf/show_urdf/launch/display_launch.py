from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch.conditions import IfCondition
from ament_index_python.packages import get_package_share_directory
def generate_launch_description():
    package_share = get_package_share_directory('show_urdf')
    return LaunchDescription([
        DeclareLaunchArgument(
            'urdf',
            default_value='leaphand_with_base.urdf',
            description='URDF file within the show_urdf package'
        ),
        DeclareLaunchArgument(
            'gui',
            default_value='True',
            description='Flag to enable joint_state_publisher GUI'
        ),
        DeclareLaunchArgument(
            'with_scene',
            default_value='True',
            description='Whether to publish static scene objects'
        ),
        DeclareLaunchArgument(
            'scene_config',
            default_value='scene_config.json',
            description='Scene configuration JSON file'
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=PathJoinSubstitution([package_share, 'rviz', 'show_urdf.rviz']),
            description='RViz config file'
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
                    package_share,
                    LaunchConfiguration('urdf')
                ])
            ]
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
            arguments=['-d', LaunchConfiguration('rviz_config')]
        )
    ])