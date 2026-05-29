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

上位机强制视觉模式、不接受下位机 mode：

```bash
ros2 launch smarthome_vision vision.launch.py \
  serial_device:=/dev/ttyACM0 \
  fake_mode:=false \
  accept_lower_mode:=false \
  default_mode:=1
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

## 上位机指定 Mode 单独调试

如果下位机暂时还没有稳定发送 `GimbalToVision.mode`，可以先禁用下位机 mode，由上位机固定视觉模式，并查看通信节点发给下位机的数据。

1. 启动视觉节点。下面命令会打开 OpenCV 调试窗口，并固定为 `test_mode=1` 物体识别：

```bash
cd /home/nvidia4/smarthome_2026_integrated_ws/smarthome_2026_integrated_ws
source /opt/ros/humble/setup.zsh
source install/setup.zsh
export DISPLAY=:0

ros2 run smarthome_vision vision_node --ros-args \
  --params-file src/smarthome_vision/src/smarthome_vision_ros2/config/vision.yaml \
  -p show_debug:=true \
  -p use_test_mode:=true \
  -p test_mode:=1 \
  -p use_local_camera:=true
```

2. 启动通信节点。`accept_lower_mode:=false` 会忽略下位机发来的 mode，`default_mode:=1` 会让通信节点持续发布上位机指定的视觉模式：

```bash
cd /home/nvidia4/smarthome_2026_integrated_ws/smarthome_2026_integrated_ws
source /opt/ros/humble/setup.zsh
source install/setup.zsh

ros2 launch robot_serial_comm robot_serial_comm.launch.py \
  serial_device:=/dev/ttyACM0 \
  baudrate:=115200 \
  fake_mode:=false \
  accept_lower_mode:=false \
  default_mode:=1
```

3. 查看发送给下位机的原始数据：

```bash
cd /home/nvidia4/smarthome_2026_integrated_ws/smarthome_2026_integrated_ws
source /opt/ros/humble/setup.zsh
source install/setup.zsh

ros2 topic echo /robot_serial_comm/raw_tx_hex
```

如果 `/smarthome/object_target` 没有消息，通信包会保持无目标状态；视觉识别到目标并发布 `ObjectTarget` 后，`raw_tx_hex` 中的 `command/class_id/x/y/z` 会随之变化。

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
