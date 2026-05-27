from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    params_file = os.path.join(
        get_package_share_directory("smarthome_vision"),
        "config",
        "vision_params.yaml"
    )

    cam_node = Node(
        package="image_tools",
        executable="cam2image",
        name="cam2image",
        output="log",   # 不在终端刷屏，写日志
        parameters=[
            {"device_id": 0}
        ],
        remappings=[
            ("image", "/image_raw")
        ]
    )

    vision_node = Node(
        package="smarthome_vision",
        executable="vision_node",
        name="smarthome_vision_node",
        output="screen",
        parameters=[
            params_file,
            {
                "use_test_mode": True,
                "test_mode": 2,
                "show_debug": True
            }
        ]
    )

    return LaunchDescription([
        cam_node,
        vision_node
    ])