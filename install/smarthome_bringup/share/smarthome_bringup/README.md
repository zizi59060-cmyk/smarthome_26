# smarthome_bringup

总启动包。它负责把导航、视觉、通信和任务状态机放在同一个 launch 中。

## 启动完整比赛流程

```bash
ros2 launch smarthome_bringup online_competition.launch.py \
  namespace:=smarthome \
  world:=smarthome_2026 \
  slam:=False \
  use_robot_state_pub:=True \
  use_rviz:=True \
  fake_comm:=False \
  serial_device:=/dev/ttyACM0 \
  auto_start:=False
```

## 只启动单雷达导航

```bash
ros2 launch smarthome_bringup navigation_only.launch.py \
  namespace:=smarthome \
  world:=smarthome_2026 \
  slam:=False
```

## 参数含义

| 参数 | 含义 |
|---|---|
| `namespace` | ROS 命名空间，单机器人推荐 `smarthome` 或空字符串 |
| `world` | 地图文件名，不带 `.yaml` 后缀 |
| `slam` | `True` 建图，`False` 定位导航 |
| `use_robot_state_pub` | 是否由导航包发布机器人 TF |
| `use_rviz` | 是否启动 RViz |
| `launch_navigation` | 是否启动导航链路 |
| `launch_vision` | 是否启动视觉节点 |
| `launch_comm` | 是否启动统一通信包 |
| `launch_mission` | 是否启动任务状态机 |
| `fake_comm` | 是否使用模拟通信 |
| `serial_device` | 下位机串口 |
| `baudrate` | 下位机串口波特率 |
| `cmd_vel_topic` | Nav2 输出速度话题 |
| `waypoint_file` | B/C/D/E/F 点位配置 |
| `auto_start` | 是否 launch 后自动开始任务 |
