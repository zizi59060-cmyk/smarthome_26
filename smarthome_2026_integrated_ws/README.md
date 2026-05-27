# smarthome_2026_integrated_ws

这是智能家居 2026 工程的集成工作空间。当前分支把上下位机通信重新收敛为一个很小的串口包 `robot_serial_comm`：上位机只向下位机发送视觉抓取状态、类别、点位、目标相机坐标和底盘速度；下位机只向上位机返回视觉模式。

旧的 `smarthome_comm` 已移除，不再包含急停、机械臂、夹爪或旧的多命令帧协议。

## 目录

```text
smarthome_2026_integrated_ws/
├── src/
│   ├── pb2025_sentry_nav/          # 导航相关源码，含 pb2025_nav_bringup
│   ├── pb2025_sentry_behavior/     # 决策启动入口，默认 smart_picking_manager
│   ├── smarthome_vision/           # 视觉识别，vision.launch.py 会带起通信
│   ├── robot_serial_comm/          # 新上下位机串口通信包
│   └── smarthome_common_interfaces/# 共享 ObjectTarget 等消息
└── README.md
```

## 通信链路

```text
Nav2 /cmd_vel ----------------------\
Vision /smarthome/object_target -----+--> robot_serial_comm --> UART --> 下位机
Decision /smarthome/zone_id --------/

下位机 -- UART --> robot_serial_comm --> /vision_mode --> smarthome_vision
```

视觉节点不再直接打开串口。`ros2 launch smarthome_vision vision.launch.py` 会同时启动视觉和 `robot_serial_comm`，所以实车运行时不要再重复启动 `robot_serial_comm`。

## 串口协议

字节序：小端。CRC：CRC16 Modbus，覆盖除 `crc16` 外的所有字节。

上位机发送给下位机：`VisionToGimbal`，固定 31 字节。

```cpp
#pragma pack(push, 1)
struct VisionToGimbal
{
  uint8_t head[2];     // 'S', 'P'
  uint8_t command;     // 1=可以抓取, 0=不能抓取
  int8_t class_id;     // -1=没有目标, 0/1/2/3=肉/蔬菜/水果/饮料
  uint8_t zone_id;     // 0=none, 1=A, 2=B, 3=C, 4=D, 5=E, 6=F
  float x;
  float y;
  float z;
  float vx;
  float vy;
  float wz;
  uint16_t crc16;
};
#pragma pack(pop)
```

下位机发送给上位机：`GimbalToVision`，固定 5 字节。

```cpp
struct __attribute__((packed)) GimbalToVision
{
  uint8_t head[2] = {'V', 'S'};
  uint8_t mode = static_cast<uint8_t>(VisionMode::IDLE);
  uint16_t crc16 = 0;
};

enum class VisionMode : uint8_t
{
  IDLE = 0,
  DETECT_OBJECT = 1,
  DETECT_QR = 2
};
```

`robot_serial_comm` 会把最近一次视觉目标和最近一次 `/cmd_vel` 合成一个包周期发送。视觉目标新鲜且 `class_id >= 0` 时 `command=1`，否则 `command=0` 且 `class_id=-1`。

## 编译

以下假设工作空间目录是 `~/ros_ws`，如果你的目录名不同，把命令里的路径替换成实际工作空间即可。

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
rosdep install -r --from-paths src --ignore-src --rosdistro humble -y
colcon build --symlink-install
source install/setup.bash
```

只编译本次改动相关包：

```bash
colcon build --symlink-install \
  --packages-up-to robot_serial_comm smarthome_vision pb2025_sentry_behavior smarthome_bringup
```

## 启动顺序

每个终端都先 source 工作空间：

```bash
cd ~/ros_ws
source install/setup.bash
```

1. 启动导航：

```bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
  use_robot_state_pub:=True \
  use_rviz:=True
```

如果已经由其它节点发布机器人 TF，可以把 `use_robot_state_pub` 改成 `False`。当前项目不启动 `standard_robot_pp_ros2` 时，通常先用 `True`。

2. 启动视觉和通信：

```bash
ros2 launch smarthome_vision vision.launch.py
```

这个 launch 已经包含 `robot_serial_comm.launch.py`，会同时启动串口通信节点，不要再重复启动 `robot_serial_comm`。

如果只想单独调通信，才使用：

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py
```

3. 启动决策：

```bash
ros2 launch pb2025_sentry_behavior pb2025_sentry_behavior_launch.py
```

默认 launch 参数：

```text
enable_smart_picking=true
enable_legacy_bt=false
```

也就是说默认启动 `smart_picking_manager`，不启动旧 BT server/client。需要临时回到旧 BT 时再显式传：

```bash
ros2 launch pb2025_sentry_behavior pb2025_sentry_behavior_launch.py \
  enable_smart_picking:=false \
  enable_legacy_bt:=true
```

## 主要 ROS 接口

| Topic | Type | 说明 |
| --- | --- | --- |
| `/smarthome/object_target` | `smarthome_common_interfaces/msg/ObjectTarget` | 视觉发布目标类别、置信度和相机坐标 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 导航或决策输出的底盘速度 |
| `/smarthome/zone_id` | `std_msgs/msg/UInt8` | 决策发布当前 A-F 点位 |
| `/smarthome/zone_name` | `std_msgs/msg/String` | 可选，给 `smart_picking_manager` 设置 A-F 点位名 |
| `/vision_mode` | `std_msgs/msg/UInt8` | 通信节点把下位机模式转发给视觉 |
| `/robot_serial_comm/raw_tx_hex` | `std_msgs/msg/String` | 调试：上位机发出的原始包 |
| `/robot_serial_comm/raw_rx_hex` | `std_msgs/msg/String` | 调试：下位机发来的原始字节 |

手动设置当前点位示例：

```bash
ros2 topic pub --once /smarthome/zone_name std_msgs/msg/String "{data: D}"
```

或者直接发布数字点位：

```bash
ros2 topic pub --once /smarthome/zone_id std_msgs/msg/UInt8 "{data: 4}"
```

## 常用调试

不接真实串口，只看打包内容：

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py fake_mode:=true
ros2 topic echo /robot_serial_comm/raw_tx_hex
```

查看下位机是否切换视觉模式：

```bash
ros2 topic echo /vision_mode
```

查看视觉是否发布目标：

```bash
ros2 topic echo /smarthome/object_target
```

查看决策当前点位：

```bash
ros2 topic echo /smarthome/zone_id
```

## 参数

`robot_serial_comm` 常用参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `serial_device` | `/dev/ttyACM0` | 下位机串口设备 |
| `baudrate` | `115200` | 波特率 |
| `fake_mode` | `false` | 不打开串口，仅发布调试 tx |
| `send_hz` | `30.0` | 上位机发送包频率 |
| `target_timeout_sec` | `0.5` | 视觉目标超时时间 |
| `target_topic` | `/smarthome/object_target` | 视觉目标 topic |
| `cmd_vel_topic` | `/cmd_vel` | 底盘速度 topic |
| `zone_id_topic` | `/smarthome/zone_id` | 当前点位 topic |
| `mode_topic` | `/vision_mode` | 视觉模式 topic |

`smarthome_vision` 常用参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `vision_mode_topic` | `/vision_mode` | 接收下位机视觉模式 |
| `object_target_topic` | `/smarthome/object_target` | 发布目标 |
| `use_test_mode` | `false` | 调试时忽略下位机模式 |
| `test_mode` | `1` | `use_test_mode=true` 时使用的模式 |

## 实车注意事项

1. 确认下位机结构体也使用 1 字节对齐，并且浮点为 IEEE754 little-endian `float`。
2. 下位机发 `GimbalToVision` 时，帧头必须是 `V S`，CRC 错误的包会被丢弃。
3. 视觉模型 engine 路径仍需要按实车路径检查 `src/smarthome_vision/src/smarthome_vision_ros2/config/vision.yaml`。
4. 串口只允许 `robot_serial_comm` 打开；视觉、导航、决策都通过 ROS topic 交互。
