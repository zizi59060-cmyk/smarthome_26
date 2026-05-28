from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_dir = get_package_share_directory("robot_serial_comm")
    params_file = os.path.join(pkg_dir, "config", "robot_serial_comm.yaml")

    return LaunchDescription([
        DeclareLaunchArgument("serial_device", default_value="/dev/ttyACM0"),
        DeclareLaunchArgument("baudrate", default_value="115200"),
        DeclareLaunchArgument("fake_mode", default_value="false"),
        DeclareLaunchArgument("target_topic", default_value="/smarthome/object_target"),
        DeclareLaunchArgument("cmd_vel_topic", default_value="/cmd_vel"),
        DeclareLaunchArgument("zone_id_topic", default_value="/smarthome/zone_id"),
        DeclareLaunchArgument("mode_topic", default_value="/vision_mode"),
        DeclareLaunchArgument("serial_state_topic", default_value="/robot_serial_comm/serial_state"),
        DeclareLaunchArgument("send_hz", default_value="30.0"),
        DeclareLaunchArgument("reconnect_interval_sec", default_value="1.0"),
        DeclareLaunchArgument("reconnect_log_interval_sec", default_value="5.0"),
        DeclareLaunchArgument("initial_connect_required", default_value="false"),
        Node(
            package="robot_serial_comm",
            executable="serial_comm_node",
            name="robot_serial_comm_node",
            output="screen",
            parameters=[
                params_file,
                {
                    "serial_device": LaunchConfiguration("serial_device"),
                    "baudrate": LaunchConfiguration("baudrate"),
                    "fake_mode": LaunchConfiguration("fake_mode"),
                    "target_topic": LaunchConfiguration("target_topic"),
                    "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                    "zone_id_topic": LaunchConfiguration("zone_id_topic"),
                    "mode_topic": LaunchConfiguration("mode_topic"),
                    "serial_state_topic": LaunchConfiguration("serial_state_topic"),
                    "send_hz": LaunchConfiguration("send_hz"),
                    "reconnect_interval_sec": LaunchConfiguration("reconnect_interval_sec"),
                    "reconnect_log_interval_sec": LaunchConfiguration("reconnect_log_interval_sec"),
                    "initial_connect_required": LaunchConfiguration("initial_connect_required"),
                },
            ],
        ),
    ])
