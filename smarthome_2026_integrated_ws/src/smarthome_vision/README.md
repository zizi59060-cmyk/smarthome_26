# smarthome_vision

`smarthome_vision` 是视觉工程目录，真正的 ROS 2 包在 `src/smarthome_vision_ros2`。它负责根据 `/vision_mode` 切换识别任务，并发布统一目标消息 `/smarthome/object_target` 给通信和决策使用。

## 链路位置

```text
下位机 --> robot_serial_comm --> /vision_mode --> smarthome_vision
smarthome_vision --> /smarthome/object_target --> robot_serial_comm
smarthome_vision --> /smarthome/object_target --> pb2025_sentry_behavior
```

视觉本身不再直接打开下位机串口。串口只由 `robot_serial_comm` 负责。

## 目录

```text
smarthome_vision/
├── README.md
├── test.raw
└── src/
    └── smarthome_vision_ros2/
        ├── config/vision.yaml
        ├── launch/vision.launch.py
        ├── src/vision_node.cpp
        ├── src/trt_detector.cpp
        ├── src/pose_solver.cpp
        └── msg/DetectedTarget.msg
```

## 启动

实车推荐启动方式：

```bash
ros2 launch smarthome_vision vision.launch.py
```

这个 launch 默认会同时 include `robot_serial_comm.launch.py`，所以不需要再开一个终端启动通信节点。

只调视觉、不启动通信：

```bash
ros2 launch smarthome_vision vision.launch.py launch_comm:=false
```

改串口设备并启动视觉通信：

```bash
ros2 launch smarthome_vision vision.launch.py \
  serial_device:=/dev/ttyACM0 \
  baudrate:=115200 \
  reconnect_interval_sec:=1.0
```

## 视觉模式

| mode | 名称 | 行为 |
| --- | --- | --- |
| `0` | `IDLE` | 空闲，不主动输出有效抓取目标 |
| `1` | `DETECT_OBJECT` | 识别物体类别，输出肉、蔬菜、水果、饮料 |
| `2` | `DETECT_QR` | 识别二维码或二维码点位相关目标 |

调试时可以在 `config/vision.yaml` 中启用测试模式：

```yaml
use_test_mode: true
test_mode: 1
```

这样视觉节点可以不依赖下位机发来的 `/vision_mode`，直接按指定模式跑。

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to smarthome_vision
source install/setup.bash
```

## 关键修改入口

| 需求 | 文件 |
| --- | --- |
| 改视觉 launch 或是否包含通信 | `src/smarthome_vision_ros2/launch/vision.launch.py` |
| 改模型路径、相机参数、阈值 | `src/smarthome_vision_ros2/config/vision.yaml` |
| 改模式订阅和目标发布逻辑 | `src/smarthome_vision_ros2/src/vision_node.cpp` |
| 改 TensorRT 推理 | `src/smarthome_vision_ros2/src/trt_detector.cpp` |
| 改目标位姿求解 | `src/smarthome_vision_ros2/src/pose_solver.cpp` |

更多节点级参数和 topic 说明见 `src/smarthome_vision_ros2/README.md`。
