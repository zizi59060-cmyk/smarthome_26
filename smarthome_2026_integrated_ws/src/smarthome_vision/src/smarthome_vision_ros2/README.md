# smarthome_vision_ros2

`smarthome_vision_ros2` 是实际编译的视觉 ROS 2 包。它读取相机图像或本地摄像头，按 `/vision_mode` 选择物体识别或二维码识别，计算目标相对相机坐标，并发布 `robot_serial_comm/msg/ObjectTarget`。

## 输入输出

| Topic | Type | 方向 | 说明 |
| --- | --- | --- | --- |
| `/vision_mode` | `std_msgs/msg/UInt8` | sub | 下位机通过通信节点下发的视觉模式 |
| `/image_raw` | `sensor_msgs/msg/Image` | sub | `use_local_camera=false` 时使用的图像输入 |
| `/smarthome/object_target` | `robot_serial_comm/msg/ObjectTarget` | pub | 给通信和决策使用的统一目标 |
| `/detected_target` | `smarthome_vision/msg/DetectedTarget` | pub | 调试用视觉原始结果 |

## 模式

| 数值 | 模式 | 说明 |
| --- | --- | --- |
| `0` | `IDLE` | 空闲 |
| `1` | `DETECT_OBJECT` | 使用 `object.engine` 识别物体 |
| `2` | `DETECT_QR` | 使用 `qrcode.engine` 识别二维码 |

如果 `use_test_mode=true`，节点忽略 `/vision_mode`，使用 `test_mode` 指定的模式。

## 启动

```bash
ros2 launch smarthome_vision vision.launch.py
```

默认会连同 `robot_serial_comm` 一起启动。只跑视觉：

```bash
ros2 launch smarthome_vision vision.launch.py launch_comm:=false
```

## 参数

主要参数在 `config/vision.yaml`：

| 参数 | 说明 |
| --- | --- |
| `image_topic` | 外部图像输入 topic |
| `vision_mode_topic` | 视觉模式 topic，默认 `/vision_mode` |
| `object_target_topic` | 统一目标输出 topic，默认 `/smarthome/object_target` |
| `target_frame_id` | 目标 pose 的坐标系 |
| `use_test_mode` / `test_mode` | 调试时强制视觉模式 |
| `use_local_camera` | 是否直接打开本地摄像头 |
| `camera_device_id` | 本地摄像头编号 |
| `camera_width` / `camera_height` / `camera_fps` | 本地摄像头采集参数 |
| `camera_matrix` / `dist_coeffs` | PnP 使用的相机内参和畸变 |
| `class_names` | 工程内使用的类别 ID |
| `class_sizes` | 每个类别对应的目标物理尺寸 |
| `object_engine_path` | 物体识别 TensorRT engine 路径 |
| `object_model_class_ids` | 物体模型输出类别到工程类别的映射 |
| `qr_engine_path` | 二维码 TensorRT engine 路径 |
| `qr_model_class_ids` | 二维码模型输出类别到工程类别的映射 |
| `qr_size` | 二维码物理尺寸 |

实车换机器后最常改的是 `object_engine_path`、`qr_engine_path`、相机内参和摄像头编号。

## 单独调试视觉和通信

联调早期可以不接受下位机发送的 mode，由上位机固定视觉模式。下面示例固定为 `mode=1` 物体识别。

1. 启动视觉节点：

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

2. 启动通信节点：

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

3. 查看上位机发送给下位机的原始数据：

```bash
cd /home/nvidia4/smarthome_2026_integrated_ws/smarthome_2026_integrated_ws
source /opt/ros/humble/setup.zsh
source install/setup.zsh

ros2 topic echo /robot_serial_comm/raw_tx_hex
```

如果只想看视觉目标输出：

```bash
ros2 topic echo /detected_target
ros2 topic echo /smarthome/object_target
```

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to smarthome_vision
source install/setup.bash
```

## 修改方式

| 需求 | 文件 |
| --- | --- |
| 改 ROS 参数、模式订阅、目标发布 | `src/vision_node.cpp` |
| 改普通检测后处理 | `src/detector.cpp` |
| 改 TensorRT 推理 | `src/trt_detector.cpp` |
| 改 PnP 和坐标解算 | `src/pose_solver.cpp` |
| 改调试消息格式 | `msg/DetectedTarget.msg` |
| 改 launch 中通信节点参数透传 | `launch/vision.launch.py` |

发布到通信节点的目标必须保持 `robot_serial_comm/msg/ObjectTarget`，这样通信、决策和 README 中的链路才能一致。
