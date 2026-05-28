# smarthome_2026_integrated_ws

这是智能家居 2026 项目的 ROS 2 集成工作空间。`zhou` 分支把工程整理成三条主链路：导航、视觉和决策；上下位机串口通信统一收敛到 `robot_serial_comm`，旧的 `smarthome_comm`、`smarthome_task_manager` 和 `smarthome_common_interfaces` 不再参与当前体系。

## 当前链路

```text
导航 /cmd_vel -------------------------\
视觉 /smarthome/object_target ----------+--> robot_serial_comm --> UART --> 下位机
决策 /smarthome/zone_id ---------------/

下位机 -- UART --> robot_serial_comm --> /vision_mode --> smarthome_vision
```

运行时的角色分工：

| 模块 | 主要包 | 作用 |
| --- | --- | --- |
| 导航 | `pb2025_nav_bringup` | 启动实车导航、TF、RViz 和 Nav2 相关节点，输出底盘速度 `/cmd_vel` |
| 视觉 | `smarthome_vision` | 根据下位机发来的视觉模式识别物体或二维码，发布 `/smarthome/object_target` |
| 通信 | `robot_serial_comm` | 打包视觉目标、点位、底盘速度并通过串口发给下位机，同时解析下位机视觉模式 |
| 决策 | `pb2025_sentry_behavior` | 默认启动 `smart_picking_manager`，发布当前 A-F 点位 `/smarthome/zone_id` |
| 总启动 | `smarthome_bringup` | 可选的一键集成启动入口，更推荐调试时按三终端顺序启动 |

## 目录说明

```text
smarthome_2026_integrated_ws/
├── src/
│   ├── pb2025_sentry_nav/              # 导航栈源码，包含 pb2025_nav_bringup
│   ├── pb2025_sentry_behavior/         # 当前默认决策入口 smart_picking_manager
│   ├── smarthome_vision/               # 视觉工程外层目录
│   │   └── src/smarthome_vision_ros2/  # 实际 ROS 2 视觉包
│   ├── robot_serial_comm/              # 新串口通信包，内含 ObjectTarget.msg
│   ├── smarthome_bringup/              # 本项目集成启动包
│   └── dependencies/                   # 第三方依赖，通常不改 README 和接口
└── README.md
```

## 串口协议

字节序：little-endian。  
CRC：CRC16 Modbus，覆盖除 `crc16` 字段外的所有字节。  
上位机发送频率默认 `30 Hz`，可通过 `send_hz` 调整。

上位机到下位机：`VisionToGimbal`，固定 `31` 字节。

```cpp
#pragma pack(push, 1)
struct VisionToGimbal
{
  uint8_t head[2];     // 'S', 'P'
  uint8_t command;     // 1=可以抓取, 0=不能抓取
  int8_t class_id;     // -1=无目标, 0=肉, 1=蔬菜, 2=水果, 3=饮料
  uint8_t zone_id;     // 0=none, 1=A, 2=B, 3=C, 4=D, 5=E, 6=F
  float x;             // 目标相对相机 x
  float y;             // 目标相对相机 y
  float z;             // 目标相对相机 z
  float vx;            // 底盘 x 速度
  float vy;            // 底盘 y 速度
  float wz;            // 底盘角速度
  uint16_t crc16;
};
#pragma pack(pop)
```

下位机到上位机：`GimbalToVision`，固定 `5` 字节。

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

`robot_serial_comm` 会把最近的视觉目标、点位和 `/cmd_vel` 合成发送包。视觉目标新鲜且 `class_id >= 0` 时 `command=1`，否则 `command=0` 且 `class_id=-1`。

## 主要 ROS 接口

| Topic | Type | 方向 | 说明 |
| --- | --- | --- | --- |
| `/smarthome/object_target` | `robot_serial_comm/msg/ObjectTarget` | vision -> comm/decision | 目标类别、置信度、相机坐标 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | nav/decision -> comm | 底盘速度 |
| `/smarthome/zone_id` | `std_msgs/msg/UInt8` | decision -> comm | 当前点位，0=None，1-6=A-F |
| `/smarthome/zone_name` | `std_msgs/msg/String` | operator -> decision | 用 A-F 字符串设置点位 |
| `/vision_mode` | `std_msgs/msg/UInt8` | comm -> vision/decision | 下位机要求的视觉模式 |
| `/robot_serial_comm/serial_state` | `std_msgs/msg/String` | comm -> debug | `connected`、`disconnected` 或 `fake` |
| `/robot_serial_comm/raw_tx_hex` | `std_msgs/msg/String` | comm -> debug | 上位机发出的原始包 |
| `/robot_serial_comm/raw_rx_hex` | `std_msgs/msg/String` | comm -> debug | 下位机发来的原始字节 |

## 编译

以下命令假设工作空间目录是 `~/ros_ws`，如果你的目录不同，把路径替换成实际目录即可。

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
rosdep install -r --from-paths src --ignore-src --rosdistro humble -y
colcon build --symlink-install
source install/setup.bash
```

只编译当前智能家居链路相关包：

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install \
  --packages-up-to robot_serial_comm smarthome_vision pb2025_sentry_behavior smarthome_bringup
source install/setup.bash
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

如果已经由别的节点发布机器人 TF，可以把 `use_robot_state_pub` 改成 `False`。当前项目不启动 `standard_robot_pp_ros2` 时，通常先用 `True`。

2. 启动视觉和通信：

```bash
ros2 launch smarthome_vision vision.launch.py
```

这个 launch 已经包含 `robot_serial_comm.launch.py`，会同时启动串口通信节点，所以不要再重复启动 `robot_serial_comm`。

如果只想单独调通信，才使用：

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py
```

3. 启动决策：

```bash
ros2 launch pb2025_sentry_behavior pb2025_sentry_behavior_launch.py
```

默认 launch 中：

```text
enable_smart_picking=true
enable_legacy_bt=false
```

也就是说默认启动 `smart_picking_manager`，不启动旧 BT server/client。需要临时回到旧 BT 时再显式切换：

```bash
ros2 launch pb2025_sentry_behavior pb2025_sentry_behavior_launch.py \
  enable_smart_picking:=false \
  enable_legacy_bt:=true
```

## 可选一键启动

集成入口在 `smarthome_bringup`：

```bash
ros2 launch smarthome_bringup online_competition.launch.py \
  use_robot_state_pub:=True \
  use_rviz:=True \
  serial_device:=/dev/ttyACM0 \
  fake_comm:=false
```

调车和排查问题时，仍然更推荐按“导航、视觉通信、决策”三终端启动，日志更清楚。

## 串口断开重连

`robot_serial_comm` 现在支持断线自动重连：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `reconnect_interval_sec` | `1.0` | 断开后尝试重新打开串口的周期 |
| `reconnect_log_interval_sec` | `5.0` | 重连失败日志节流周期，避免刷屏 |
| `initial_connect_required` | `false` | `false` 时没有串口也能启动并等待重连；`true` 时初始打开失败直接退出 |
| `serial_state_topic` | `/robot_serial_comm/serial_state` | 发布 `connected`、`disconnected`、`fake` |

示例：

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py \
  serial_device:=/dev/ttyACM0 \
  reconnect_interval_sec:=0.5 \
  initial_connect_required:=false
```

## 常用调试

不接真实串口，只看打包内容：

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py fake_mode:=true
ros2 topic echo /robot_serial_comm/raw_tx_hex
```

查看串口状态：

```bash
ros2 topic echo /robot_serial_comm/serial_state
```

查看下位机视觉模式：

```bash
ros2 topic echo /vision_mode
```

查看视觉目标：

```bash
ros2 topic echo /smarthome/object_target
```

手动设置点位：

```bash
ros2 topic pub --once /smarthome/zone_name std_msgs/msg/String "{data: D}"
```

或者直接发布数字点位：

```bash
ros2 topic pub --once /smarthome/zone_id std_msgs/msg/UInt8 "{data: 4}"
```

## 修改入口

| 想改什么 | 文件 |
| --- | --- |
| 串口结构体、CRC、解析逻辑 | `src/robot_serial_comm/robot_serial_comm_py/protocol.py` |
| 串口打开、关闭、读写、断线判定 | `src/robot_serial_comm/robot_serial_comm_py/serial_transport.py` |
| ROS topic 到串口包的映射 | `src/robot_serial_comm/robot_serial_comm_py/serial_comm_node.py` |
| 通信默认参数 | `src/robot_serial_comm/config/robot_serial_comm.yaml` |
| 视觉模式、模型路径、相机参数 | `src/smarthome_vision/src/smarthome_vision_ros2/config/vision.yaml` |
| 视觉节点代码 | `src/smarthome_vision/src/smarthome_vision_ros2/src/vision_node.cpp` |
| 点位决策逻辑 | `src/pb2025_sentry_behavior/scripts/smart_picking_manager.py` |
| 总启动参数 | `src/smarthome_bringup/launch/online_competition.launch.py` |

## 实车注意事项

1. 下位机结构体必须 1 字节对齐，`float` 使用 IEEE754 little-endian。
2. 下位机发送 `GimbalToVision` 时帧头必须是 `V S`，CRC 错误的包会被丢弃。
3. 串口只允许 `robot_serial_comm` 打开。视觉、导航、决策都通过 ROS topic 交互。
4. 视觉 TensorRT engine 路径需要按实车检查 `src/smarthome_vision/src/smarthome_vision_ros2/config/vision.yaml`。
5. 当前 `ObjectTarget.msg` 已移动到 `robot_serial_comm/msg/ObjectTarget.msg`，不要再依赖 `smarthome_common_interfaces`。
