# smarthome_vision

视觉包负责目标检测和位姿解算，不再直接打开下位机串口。

## 输入输出

| Topic | Type | 说明 |
| --- | --- | --- |
| `/vision_mode` | `std_msgs/msg/UInt8` | 通信节点转发的下位机模式 |
| `/smarthome/object_target` | `robot_serial_comm/msg/ObjectTarget` | 视觉目标输出 |
| `/detected_target` | `smarthome_vision/msg/DetectedTarget` | 调试用视觉原始输出 |

## 启动

```bash
ros2 launch smarthome_vision vision.launch.py
```

这个 launch 默认包含 `robot_serial_comm.launch.py`，实车时不要在另一个终端重复启动通信节点。

只调视觉、不启通信：

```bash
ros2 launch smarthome_vision vision.launch.py launch_comm:=false
```

调试时强制视觉模式：

```yaml
use_test_mode: true
test_mode: 1
```
