from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    vision_dir = get_package_share_directory("smarthome_vision")
    comm_dir = get_package_share_directory("robot_serial_comm")

    default_params = os.path.join(vision_dir, "config", "vision.yaml")
    comm_launch = os.path.join(comm_dir, "launch", "robot_serial_comm.launch.py")

    return LaunchDescription([
        DeclareLaunchArgument("params_file", default_value=default_params),
        DeclareLaunchArgument("launch_comm", default_value="true"),
        DeclareLaunchArgument("serial_device", default_value="/dev/ttyACM0"),
        DeclareLaunchArgument("baudrate", default_value="115200"),
        DeclareLaunchArgument("fake_mode", default_value="false"),
        DeclareLaunchArgument("target_topic", default_value="/smarthome/object_target"),
        DeclareLaunchArgument("cmd_vel_topic", default_value="/cmd_vel"),
        DeclareLaunchArgument("zone_id_topic", default_value="/smarthome/zone_id"),
        DeclareLaunchArgument("mode_topic", default_value="/vision_mode"),

        Node(
            package="smarthome_vision",
            executable="vision_node",
            name="smarthome_vision_node",
            output="screen",
            parameters=[LaunchConfiguration("params_file")],
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(comm_launch),
            condition=IfCondition(LaunchConfiguration("launch_comm")),
            launch_arguments={
                "serial_device": LaunchConfiguration("serial_device"),
                "baudrate": LaunchConfiguration("baudrate"),
                "fake_mode": LaunchConfiguration("fake_mode"),
                "target_topic": LaunchConfiguration("target_topic"),
                "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                "zone_id_topic": LaunchConfiguration("zone_id_topic"),
                "mode_topic": LaunchConfiguration("mode_topic"),
            }.items(),
        ),
    ])
