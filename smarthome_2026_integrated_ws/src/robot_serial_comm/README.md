# robot_serial_comm

`robot_serial_comm` 是当前工程唯一负责上下位机串口收发的 ROS 2 包。它不再包含急停、机械臂、夹爪等旧协议，只做三件事：

1. 接收视觉目标 `/smarthome/object_target`。
2. 接收底盘速度 `/cmd_vel` 和当前点位 `/smarthome/zone_id`。
3. 打包成 `VisionToGimbal` 发给下位机，并把下位机 `GimbalToVision` 模式转成 `/vision_mode`。

`ObjectTarget.msg` 已经放在本包内，视觉和决策都直接依赖 `robot_serial_comm`。

## 协议

字节序：little-endian。  
CRC：CRC16 Modbus，覆盖除 `crc16` 之外的所有字节。

上位机到下位机：`VisionToGimbal`，固定 `31` 字节。

```cpp
#pragma pack(push, 1)
struct VisionToGimbal
{
  uint8_t head[2];     // 'S', 'P'
  uint8_t command;     // 1=可以抓取, 0=不能抓取
  int8_t class_id;     // -1=无目标, 0=肉, 1=蔬菜, 2=水果, 3=饮料
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

发送规则：

| 字段 | 来源 |
| --- | --- |
| `command` | 视觉目标未超时且 `class_id >= 0` 时为 `1`，否则为 `0` |
| `class_id` | `/smarthome/object_target.class_id`，无目标时 `-1` |
| `zone_id` | `/smarthome/zone_id`，范围 `0-6` |
| `x/y/z` | 目标在相机坐标系下的位置 |
| `vx/vy/wz` | `/cmd_vel` 中的底盘速度 |

## ObjectTarget.msg

```text
builtin_interfaces/Time stamp
int32 class_id
geometry_msgs/PoseStamped pose
float32 score
uint8 source
string label

uint8 SOURCE_OBJECT=0
uint8 SOURCE_QR=1
uint8 SOURCE_MANUAL=2
```

## Topic

| Topic | Type | 方向 | 说明 |
| --- | --- | --- | --- |
| `/smarthome/object_target` | `robot_serial_comm/msg/ObjectTarget` | sub | 视觉目标 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | sub | 底盘速度 |
| `/smarthome/zone_id` | `std_msgs/msg/UInt8` | sub | 当前点位 |
| `/vision_mode` | `std_msgs/msg/UInt8` | pub | 下位机视觉模式 |
| `/robot_serial_comm/serial_state` | `std_msgs/msg/String` | pub | 串口状态 |
| `/robot_serial_comm/raw_tx_hex` | `std_msgs/msg/String` | pub | 调试用发送包 |
| `/robot_serial_comm/raw_rx_hex` | `std_msgs/msg/String` | pub | 调试用接收字节 |

## 启动

单独启动通信：

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py
```

常用参数：

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py \
  serial_device:=/dev/ttyACM0 \
  baudrate:=115200 \
  fake_mode:=false \
  reconnect_interval_sec:=1.0
```

实车完整运行时通常不用单独启动本包，因为：

```bash
ros2 launch smarthome_vision vision.launch.py
```

已经包含 `robot_serial_comm.launch.py`。

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `serial_device` | `/dev/ttyACM0` | 下位机串口设备 |
| `baudrate` | `115200` | 波特率 |
| `fake_mode` | `false` | 不打开真实串口，只发布调试 tx |
| `read_hz` | `200.0` | 串口读取轮询频率 |
| `send_hz` | `30.0` | 上位机发送频率 |
| `mode_pub_hz` | `10.0` | `/vision_mode` 保持发布频率 |
| `target_timeout_sec` | `0.5` | 视觉目标超时时间 |
| `reconnect_interval_sec` | `1.0` | 断开后重连周期 |
| `reconnect_log_interval_sec` | `5.0` | 重连失败日志间隔 |
| `initial_connect_required` | `false` | 初始打不开串口时是否直接退出 |
| `target_topic` | `/smarthome/object_target` | 视觉目标 topic |
| `cmd_vel_topic` | `/cmd_vel` | 底盘速度 topic |
| `zone_id_topic` | `/smarthome/zone_id` | 点位 topic |
| `mode_topic` | `/vision_mode` | 视觉模式 topic |
| `serial_state_topic` | `/robot_serial_comm/serial_state` | 串口状态 topic |

## 断线重连

节点启动后会先尝试打开 `serial_device`。如果失败且 `initial_connect_required=false`，节点会继续运行，并按 `reconnect_interval_sec` 周期重试。运行中读写出现异常时会关闭当前串口对象，发布 `disconnected`，随后进入同样的重连流程。重新打开成功后会清空接收缓存并发布 `connected`。

调试命令：

```bash
ros2 topic echo /robot_serial_comm/serial_state
ros2 topic echo /robot_serial_comm/raw_tx_hex
ros2 topic echo /robot_serial_comm/raw_rx_hex
```

## 修改入口

| 需求 | 文件 |
| --- | --- |
| 改结构体字段、帧头、CRC | `robot_serial_comm_py/protocol.py` |
| 改串口打开、关闭、读写、断线判定 | `robot_serial_comm_py/serial_transport.py` |
| 改 topic 到协议字段的映射 | `robot_serial_comm_py/serial_comm_node.py` |
| 改默认参数 | `config/robot_serial_comm.yaml` |
| 改 launch 参数 | `launch/robot_serial_comm.launch.py` |

改协议后建议同步做三件事：

1. 修改上面的结构体文档。
2. 修改下位机结构体并确认 1 字节对齐。
3. 用 `fake_mode:=true` 查看 `/robot_serial_comm/raw_tx_hex` 是否符合预期。
