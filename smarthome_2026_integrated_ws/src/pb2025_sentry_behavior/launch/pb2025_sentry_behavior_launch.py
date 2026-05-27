# Copyright 2025 Lihan Chen
#
# Licensed under the Apache License, Version 2.0.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    bringup_dir = get_package_share_directory("pb2025_sentry_behavior")

    namespace = LaunchConfiguration("namespace")
    use_sim_time = LaunchConfiguration("use_sim_time")
    params_file = LaunchConfiguration("params_file")
    log_level = LaunchConfiguration("log_level")
    enable_smart_picking = LaunchConfiguration("enable_smart_picking")
    enable_legacy_bt = LaunchConfiguration("enable_legacy_bt")

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key=namespace,
            param_rewrites={"use_sim_time": use_sim_time},
            convert_types=True,
        ),
        allow_substs=True,
    )

    bringup_cmd_group = GroupAction(
        [
            PushRosNamespace(namespace=namespace),
            SetRemap("/tf", "tf"),
            SetRemap("/tf_static", "tf_static"),
            Node(
                package="pb2025_sentry_behavior",
                executable="smart_picking_manager.py",
                name="smart_picking_manager",
                output="screen",
                condition=IfCondition(enable_smart_picking),
                parameters=[
                    {
                        "auto_start": LaunchConfiguration("smart_picking_auto_start"),
                        "target_topic": LaunchConfiguration("target_topic"),
                        "vision_mode_topic": LaunchConfiguration("vision_mode_topic"),
                        "zone_id_topic": LaunchConfiguration("zone_id_topic"),
                        "zone_name_topic": LaunchConfiguration("zone_name_topic"),
                        "initial_zone": LaunchConfiguration("initial_zone"),
                        "publish_hz": LaunchConfiguration("publish_hz"),
                    }
                ],
                arguments=["--ros-args", "--log-level", log_level],
            ),
            Node(
                package="pb2025_sentry_behavior",
                executable="pb2025_sentry_behavior_server",
                name="pb2025_sentry_behavior_server",
                output="screen",
                condition=IfCondition(enable_legacy_bt),
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
            ),
            Node(
                package="pb2025_sentry_behavior",
                executable="pb2025_sentry_behavior_client",
                name="pb2025_sentry_behavior_client",
                output="screen",
                condition=IfCondition(enable_legacy_bt),
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
            ),
        ]
    )

    return LaunchDescription(
        [
            SetEnvironmentVariable("RCUTILS_LOGGING_BUFFERED_STREAM", "1"),
            SetEnvironmentVariable("RCUTILS_COLORIZED_OUTPUT", "1"),
            DeclareLaunchArgument("namespace", default_value="", description="Top-level namespace"),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "params_file",
                default_value=os.path.join(bringup_dir, "params", "sentry_behavior.yaml"),
            ),
            DeclareLaunchArgument("log_level", default_value="info"),
            DeclareLaunchArgument("enable_smart_picking", default_value="true"),
            DeclareLaunchArgument("enable_legacy_bt", default_value="false"),
            DeclareLaunchArgument("smart_picking_auto_start", default_value="true"),
            DeclareLaunchArgument("target_topic", default_value="/smarthome/object_target"),
            DeclareLaunchArgument("vision_mode_topic", default_value="/vision_mode"),
            DeclareLaunchArgument("zone_id_topic", default_value="/smarthome/zone_id"),
            DeclareLaunchArgument("zone_name_topic", default_value="/smarthome/zone_name"),
            DeclareLaunchArgument("initial_zone", default_value="NONE"),
            DeclareLaunchArgument("publish_hz", default_value="10.0"),
            bringup_cmd_group,
        ]
    )
