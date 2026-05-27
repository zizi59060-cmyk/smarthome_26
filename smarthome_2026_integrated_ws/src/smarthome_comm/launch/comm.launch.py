from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_dir = get_package_share_directory('smarthome_comm')
    default_params = os.path.join(pkg_dir, 'config', 'comm.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('serial_device', default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('baudrate', default_value='115200'),
        DeclareLaunchArgument('fake_mode', default_value='true'),
        DeclareLaunchArgument('cmd_vel_topic', default_value='/cmd_vel'),
        Node(
            package='smarthome_comm',
            executable='comm_node',
            name='smarthome_comm_node',
            output='screen',
            parameters=[
                LaunchConfiguration('params_file'),
                {
                    'serial_device': LaunchConfiguration('serial_device'),
                    'baudrate': LaunchConfiguration('baudrate'),
                    'fake_mode': LaunchConfiguration('fake_mode'),
                    'cmd_vel_topic': LaunchConfiguration('cmd_vel_topic'),
                },
            ],
        ),
    ])
