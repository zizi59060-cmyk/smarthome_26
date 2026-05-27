# smarthome_bringup

总启动包会按当前工程约定启动三条链路：

- 导航：`pb2025_nav_bringup`
- 视觉和通信：`smarthome_vision`，其 launch 内部包含 `robot_serial_comm`
- 决策：`pb2025_sentry_behavior`，默认 `smart_picking_manager`

## 完整启动

```bash
ros2 launch smarthome_bringup online_competition.launch.py \
  use_robot_state_pub:=True \
  use_rviz:=True \
  serial_device:=/dev/ttyACM0 \
  fake_comm:=false
```

## 常用参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `launch_navigation` | `true` | 是否启动导航 |
| `launch_vision` | `true` | 是否启动视觉和通信 |
| `launch_decision` | `true` | 是否启动 smart picking 决策 |
| `serial_device` | `/dev/ttyACM0` | 下位机串口 |
| `baudrate` | `115200` | 串口波特率 |
| `fake_comm` | `false` | 通信节点 fake 模式 |
| `cmd_vel_topic` | `/cmd_vel` | 底盘速度 |
| `target_topic` | `/smarthome/object_target` | 视觉目标 |
| `zone_id_topic` | `/smarthome/zone_id` | 当前点位 |
| `mode_topic` | `/vision_mode` | 下位机视觉模式 |

更推荐按根目录 README 的三终端顺序分别启动，排查问题时更清楚。
