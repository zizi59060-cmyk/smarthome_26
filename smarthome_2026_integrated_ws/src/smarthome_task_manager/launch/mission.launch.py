from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_dir = get_package_share_directory('smarthome_task_manager')
    default_waypoints = os.path.join(pkg_dir, 'config', 'waypoints.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('waypoint_file', default_value=default_waypoints),
        DeclareLaunchArgument('auto_start', default_value='false'),
        Node(
            package='smarthome_task_manager',
            executable='mission_node',
            name='smarthome_mission_node',
            output='screen',
            parameters=[{
                'waypoint_file': LaunchConfiguration('waypoint_file'),
                'auto_start': LaunchConfiguration('auto_start'),
            }],
        ),
    ])
