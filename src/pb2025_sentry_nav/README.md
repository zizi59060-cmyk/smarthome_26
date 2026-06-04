# pb2025_sentry_nav

`pb2025_sentry_nav` 是本工作空间中的导航栈目录，主要来自原哨兵导航工程。当前智能家居链路只把它作为“导航和底盘速度来源”，通过 `/cmd_vel` 与 `robot_serial_comm` 连接，不直接参与视觉和串口协议。

## 链路位置

```text
pb2025_nav_bringup / Nav2 --> /cmd_vel --> robot_serial_comm --> 下位机
```

导航负责定位、规划、路径跟踪和速度输出；通信节点只读取 `/cmd_vel` 中的 `linear.x`、`linear.y`、`angular.z` 并写入 `VisionToGimbal.vx/vy/wz`。

## 当前推荐启动

实车导航：

```bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
  use_robot_state_pub:=True \
  use_rviz:=True
```

如果已有其它节点发布机器人 TF，可以把 `use_robot_state_pub` 改成 `False`。当前智能家居项目不启动 `standard_robot_pp_ros2` 时，通常先用 `True`。

仿真导航仍可使用原工程 launch，例如：

```bash
ros2 launch pb2025_nav_bringup rm_navigation_simulation_launch.py
```

## 目录

| 子目录 | 作用 |
| --- | --- |
| `pb2025_nav_bringup` | 导航 launch、Nav2 参数、地图和 RViz 配置 |
| `pb2025_sentry_nav` | 原导航功能包 |
| `pb_omni_pid_pursuit_controller` | 全向底盘路径跟踪控制器 |
| `pb_nav2_plugins` | Nav2 插件 |
| `point_lio` | LiDAR 里程计 |
| `small_gicp_relocalization` | 点云重定位 |
| `livox_ros_driver2` | Livox 雷达驱动 |
| `sensor_scan_generation` | 点云到局部扫描/地形信息 |
| `terrain_analysis` / `terrain_analysis_ext` | 地形分析 |
| `pointcloud_to_laserscan` | 点云转 LaserScan |
| `pb_teleop_twist_joy` | 手柄遥控 |
| `fake_vel_transform` | 仿真或调试速度坐标转换 |

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to pb2025_nav_bringup
source install/setup.bash
```

## 修改方式

| 需求 | 文件或目录 |
| --- | --- |
| 改实车导航启动 | `pb2025_nav_bringup/launch/rm_navigation_reality_launch.py` |
| 改 Nav2 参数 | `pb2025_nav_bringup/config/reality/nav2_params.yaml` |
| 改地图 | `pb2025_nav_bringup/map/` |
| 改 RViz | `pb2025_nav_bringup/rviz/nav2_default_view.rviz` |
| 改路径跟踪控制器 | `pb_omni_pid_pursuit_controller/` |
| 改重定位 | `small_gicp_relocalization/` |
| 改雷达驱动配置 | `pb2025_nav_bringup/config/reality/mid360_user_config.json` |

和串口协议相关的修改不要放在导航包里。底盘速度只需要保证 `/cmd_vel` 正常发布即可。
