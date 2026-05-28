# smarthome_bringup

`smarthome_bringup` 是本项目的一键集成启动包。它按当前工程约定启动三条链路：

1. 导航：`pb2025_nav_bringup`
2. 视觉和通信：`smarthome_vision`，内部包含 `robot_serial_comm`
3. 决策：`pb2025_sentry_behavior`，默认 `smart_picking_manager`

调车时更推荐按根目录 README 的三终端顺序启动；比赛或整体联调时可以使用本包。

## 链路

```text
online_competition.launch.py
├── pb2025_nav_bringup/rm_navigation_reality_launch.py
├── smarthome_vision/vision.launch.py
│   └── robot_serial_comm/robot_serial_comm.launch.py
└── pb2025_sentry_behavior/pb2025_sentry_behavior_launch.py
```

## 启动

```bash
ros2 launch smarthome_bringup online_competition.launch.py \
  use_robot_state_pub:=True \
  use_rviz:=True \
  serial_device:=/dev/ttyACM0 \
  fake_comm:=false
```

只启动视觉和通信：

```bash
ros2 launch smarthome_bringup online_competition.launch.py \
  launch_navigation:=false \
  launch_decision:=false
```

只启动导航：

```bash
ros2 launch smarthome_bringup online_competition.launch.py \
  launch_vision:=false \
  launch_decision:=false
```

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `namespace` | 空 | ROS namespace |
| `world` | `smarthome_2026` | 传给导航 launch 的地图/世界名称 |
| `slam` | `False` | 导航是否启用 SLAM |
| `use_robot_state_pub` | `True` | 是否由导航链路启动 robot_state_publisher |
| `use_rviz` | `True` | 是否启动 RViz |
| `launch_navigation` | `true` | 是否启动导航 |
| `launch_vision` | `true` | 是否启动视觉和通信 |
| `launch_decision` | `true` | 是否启动决策 |
| `fake_comm` | `false` | 通信节点 fake 模式 |
| `serial_device` | `/dev/ttyACM0` | 下位机串口 |
| `baudrate` | `115200` | 串口波特率 |
| `reconnect_interval_sec` | `1.0` | 串口重连周期 |
| `reconnect_log_interval_sec` | `5.0` | 重连失败日志间隔 |
| `initial_connect_required` | `false` | 初始打不开串口时是否退出 |
| `cmd_vel_topic` | `/cmd_vel` | 底盘速度 |
| `target_topic` | `/smarthome/object_target` | 视觉目标 |
| `zone_id_topic` | `/smarthome/zone_id` | 点位数字 |
| `zone_name_topic` | `/smarthome/zone_name` | 点位名称 |
| `mode_topic` | `/vision_mode` | 下位机视觉模式 |
| `serial_state_topic` | `/robot_serial_comm/serial_state` | 串口状态 |

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to smarthome_bringup
source install/setup.bash
```

## 修改方式

| 需求 | 文件 |
| --- | --- |
| 改一键启动包含哪些链路 | `launch/online_competition.launch.py` |
| 改通信参数透传 | `launch/online_competition.launch.py` 和 `robot_serial_comm/launch/robot_serial_comm.launch.py` |
| 改视觉是否默认带通信 | `smarthome_vision/src/smarthome_vision_ros2/launch/vision.launch.py` |
| 改决策默认是否使用 smart manager | `pb2025_sentry_behavior/launch/pb2025_sentry_behavior_launch.py` |

如果某条链路启动失败，先单独启动对应包确认日志，再回到本总启动包。
