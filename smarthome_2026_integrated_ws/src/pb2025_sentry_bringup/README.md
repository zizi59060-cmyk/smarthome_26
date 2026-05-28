# pb2025_sentry_bringup

`pb2025_sentry_bringup` 是原哨兵工程的启动包，保留给旧导航、旧视觉和原哨兵整车流程使用。当前智能家居 2026 链路的推荐入口是根目录 README 中的三终端顺序，或 `smarthome_bringup/online_competition.launch.py`。

## 当前项目中的定位

```text
当前推荐:
pb2025_nav_bringup + smarthome_vision + robot_serial_comm + pb2025_sentry_behavior

旧入口:
pb2025_sentry_bringup/bringup.launch.py
pb2025_sentry_bringup/bringup_nav.launch.py
pb2025_sentry_bringup/bringup_vision.launch.py
pb2025_sentry_bringup/bringup_sp.launch.py
```

如果你正在跑智能家居项目，不建议直接从本包启动完整系统，因为这里仍包含一些原哨兵链路依赖，例如 `standard_robot_pp_ros2` 和 `pb2025_vision_bringup`。

## 启动文件

| Launch | 说明 |
| --- | --- |
| `bringup.launch.py` | 原哨兵总启动 |
| `bringup_nav.launch.py` | 原导航链路启动 |
| `bringup_vision.launch.py` | 原视觉链路启动 |
| `bringup_sp.launch.py` | 原串口或底盘相关链路 |
| `rviz_launch.py` | RViz 配置启动 |
| `record_rosbag_launch.py` | rosbag 记录 |

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to pb2025_sentry_bringup
source install/setup.bash
```

## 修改方式

| 需求 | 文件 |
| --- | --- |
| 改旧总启动 | `launch/bringup.launch.py` |
| 改旧导航启动 | `launch/bringup_nav.launch.py` |
| 改旧视觉启动 | `launch/bringup_vision.launch.py` |
| 改 RViz 配置 | `rviz/sentry_default_view.rviz` |
| 改旧参数 | `params/node_params.yaml` |

新串口协议不要在本包中修改。当前协议入口在 `robot_serial_comm`。
