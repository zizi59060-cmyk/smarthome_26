from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    nav_launch = os.path.join(get_package_share_directory('pb2025_nav_bringup'), 'launch', 'rm_navigation_reality_launch.py')
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='smarthome'),
        DeclareLaunchArgument('world', default_value='smarthome_2026'),
        DeclareLaunchArgument('slam', default_value='False'),
        DeclareLaunchArgument('use_robot_state_pub', default_value='True'),
        DeclareLaunchArgument('use_rviz', default_value='True'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav_launch),
            launch_arguments={
                'namespace': LaunchConfiguration('namespace'),
                'world': LaunchConfiguration('world'),
                'slam': LaunchConfiguration('slam'),
                'use_robot_state_pub': LaunchConfiguration('use_robot_state_pub'),
                'use_rviz': LaunchConfiguration('use_rviz'),
            }.items(),
        ),
    ])
