# auto_aim_interfaces

`auto_aim_interfaces` 是原 RM 视觉/自瞄链路的消息包。当前智能家居主链路不依赖它，视觉目标统一使用 `robot_serial_comm/msg/ObjectTarget`。

## 当前项目中的定位

```text
当前智能家居链路:
smarthome_vision --> robot_serial_comm/msg/ObjectTarget --> robot_serial_comm / pb2025_sentry_behavior

旧自瞄链路:
auto_aim_interfaces/msg/Target 等消息
```

保留本包是为了旧行为树、旧视觉代码或上游导航/哨兵工程仍能编译。

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to auto_aim_interfaces
source install/setup.bash
```

## 修改方式

| 需求 | 文件 |
| --- | --- |
| 改旧自瞄目标消息 | `msg/Target.msg` |
| 改装甲板调试消息 | `msg/Armor.msg`、`msg/Armors.msg`、`msg/DebugArmor.msg`、`msg/DebugArmors.msg` |
| 改灯条调试消息 | `msg/DebugLight.msg`、`msg/DebugLights.msg` |

新智能家居通信不要在这里加消息。目标消息入口是 `robot_serial_comm/msg/ObjectTarget.msg`。
