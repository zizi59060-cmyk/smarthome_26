from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def pkg_share(name: str) -> str:
    return get_package_share_directory(name)


def generate_launch_description():
    nav_launch = os.path.join(
        pkg_share("pb2025_nav_bringup"), "launch", "rm_navigation_reality_launch.py")
    vision_launch = os.path.join(
        pkg_share("smarthome_vision"), "launch", "vision.launch.py")
    behavior_launch = os.path.join(
        pkg_share("pb2025_sentry_behavior"), "launch", "pb2025_sentry_behavior_launch.py")

    return LaunchDescription([
        DeclareLaunchArgument("namespace", default_value=""),
        DeclareLaunchArgument("world", default_value="smarthome_2026"),
        DeclareLaunchArgument("slam", default_value="False"),
        DeclareLaunchArgument("use_robot_state_pub", default_value="True"),
        DeclareLaunchArgument("use_rviz", default_value="True"),
        DeclareLaunchArgument("launch_navigation", default_value="true"),
        DeclareLaunchArgument("launch_vision", default_value="true"),
        DeclareLaunchArgument("launch_decision", default_value="true"),
        DeclareLaunchArgument("fake_comm", default_value="false"),
        DeclareLaunchArgument("serial_device", default_value="/dev/ttyACM0"),
        DeclareLaunchArgument("baudrate", default_value="115200"),
        DeclareLaunchArgument("cmd_vel_topic", default_value="/cmd_vel"),
        DeclareLaunchArgument("target_topic", default_value="/smarthome/object_target"),
        DeclareLaunchArgument("zone_id_topic", default_value="/smarthome/zone_id"),
        DeclareLaunchArgument("zone_name_topic", default_value="/smarthome/zone_name"),
        DeclareLaunchArgument("mode_topic", default_value="/vision_mode"),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav_launch),
            condition=IfCondition(LaunchConfiguration("launch_navigation")),
            launch_arguments={
                "namespace": LaunchConfiguration("namespace"),
                "world": LaunchConfiguration("world"),
                "slam": LaunchConfiguration("slam"),
                "use_robot_state_pub": LaunchConfiguration("use_robot_state_pub"),
                "use_rviz": LaunchConfiguration("use_rviz"),
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(vision_launch),
            condition=IfCondition(LaunchConfiguration("launch_vision")),
            launch_arguments={
                "launch_comm": "true",
                "serial_device": LaunchConfiguration("serial_device"),
                "baudrate": LaunchConfiguration("baudrate"),
                "fake_mode": LaunchConfiguration("fake_comm"),
                "target_topic": LaunchConfiguration("target_topic"),
                "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                "zone_id_topic": LaunchConfiguration("zone_id_topic"),
                "mode_topic": LaunchConfiguration("mode_topic"),
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(behavior_launch),
            condition=IfCondition(LaunchConfiguration("launch_decision")),
            launch_arguments={
                "namespace": LaunchConfiguration("namespace"),
                "enable_smart_picking": "true",
                "enable_legacy_bt": "false",
                "target_topic": LaunchConfiguration("target_topic"),
                "vision_mode_topic": LaunchConfiguration("mode_topic"),
                "zone_id_topic": LaunchConfiguration("zone_id_topic"),
                "zone_name_topic": LaunchConfiguration("zone_name_topic"),
            }.items(),
        ),
    ])
