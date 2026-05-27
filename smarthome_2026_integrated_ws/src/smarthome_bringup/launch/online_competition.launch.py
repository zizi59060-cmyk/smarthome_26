from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def pkg_share(name: str) -> str:
    return get_package_share_directory(name)


def generate_launch_description():
    bringup_dir = pkg_share('smarthome_bringup')
    comm_dir = pkg_share('smarthome_comm')
    mission_dir = pkg_share('smarthome_task_manager')

    nav_launch = os.path.join(pkg_share('pb2025_nav_bringup'), 'launch', 'rm_navigation_reality_launch.py')
    comm_launch = os.path.join(comm_dir, 'launch', 'comm.launch.py')
    mission_launch = os.path.join(mission_dir, 'launch', 'mission.launch.py')
    vision_params = os.path.join(bringup_dir, 'config', 'vision_override.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='smarthome'),
        DeclareLaunchArgument('world', default_value='smarthome_2026'),
        DeclareLaunchArgument('slam', default_value='False'),
        DeclareLaunchArgument('use_robot_state_pub', default_value='True'),
        DeclareLaunchArgument('use_rviz', default_value='True'),
        DeclareLaunchArgument('launch_navigation', default_value='true'),
        DeclareLaunchArgument('launch_vision', default_value='true'),
        DeclareLaunchArgument('launch_comm', default_value='true'),
        DeclareLaunchArgument('launch_mission', default_value='true'),
        DeclareLaunchArgument('fake_comm', default_value='true'),
        DeclareLaunchArgument('serial_device', default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('baudrate', default_value='115200'),
        DeclareLaunchArgument('cmd_vel_topic', default_value='/cmd_vel'),
        DeclareLaunchArgument('waypoint_file', default_value=os.path.join(mission_dir, 'config', 'waypoints.yaml')),
        DeclareLaunchArgument('auto_start', default_value='false'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav_launch),
            condition=IfCondition(LaunchConfiguration('launch_navigation')),
            launch_arguments={
                'namespace': LaunchConfiguration('namespace'),
                'world': LaunchConfiguration('world'),
                'slam': LaunchConfiguration('slam'),
                'use_robot_state_pub': LaunchConfiguration('use_robot_state_pub'),
                'use_rviz': LaunchConfiguration('use_rviz'),
            }.items(),
        ),

        # Do not use the original vision launch here because some versions expect a different config filename.
        # Start the known executable directly and override serial_device to avoid duplicated lower-computer I/O.
        Node(
            package='smarthome_vision',
            executable='vision_node',
            name='smarthome_vision_node',
            output='screen',
            parameters=[vision_params],
            condition=IfCondition(LaunchConfiguration('launch_vision')),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(comm_launch),
            condition=IfCondition(LaunchConfiguration('launch_comm')),
            launch_arguments={
                'fake_mode': LaunchConfiguration('fake_comm'),
                'serial_device': LaunchConfiguration('serial_device'),
                'baudrate': LaunchConfiguration('baudrate'),
                'cmd_vel_topic': LaunchConfiguration('cmd_vel_topic'),
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(mission_launch),
            condition=IfCondition(LaunchConfiguration('launch_mission')),
            launch_arguments={
                'waypoint_file': LaunchConfiguration('waypoint_file'),
                'auto_start': LaunchConfiguration('auto_start'),
            }.items(),
        ),
    ])
