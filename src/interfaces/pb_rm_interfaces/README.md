# pb_rm_interfaces

`pb_rm_interfaces` 是原 StandardRobot++ / RoboMaster 工程使用的通用接口包，包含云台、发射、裁判系统等消息。当前智能家居主链路不再使用这些接口做上下位机通信。

## 当前项目中的定位

```text
当前上下位机通信:
robot_serial_comm/msg/ObjectTarget + VisionToGimbal/GimbalToVision

旧 RoboMaster 通用接口:
pb_rm_interfaces/msg/*
```

保留本包是为了导航、旧 BehaviorTree 或原哨兵代码的兼容编译。新的抓取通信协议不要在本包里扩展。

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to pb_rm_interfaces
source install/setup.bash
```

## 修改方式

| 需求 | 目录 |
| --- | --- |
| 改 RoboMaster 通用消息 | `msg/` |
| 改服务接口 | `srv/` |
| 改 action 接口 | `action/` |

如果是智能家居视觉目标、点位、底盘速度或下位机视觉模式，请改 `robot_serial_comm`，不要改这里。
