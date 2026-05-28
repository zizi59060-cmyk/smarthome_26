# robot_serial_comm

`robot_serial_comm` 是本工程唯一负责上下位机串口收发的 ROS 2 包。它发送视觉目标、点位和底盘速度，接收下位机发来的视觉模式。

## Packet Layout

上位机到下位机：`VisionToGimbal`，31 字节，小端序，CRC16 Modbus 覆盖除 `crc16` 之外的所有字节。

```cpp
#pragma pack(push, 1)
struct VisionToGimbal
{
  uint8_t head[2];   // 'S', 'P'
  uint8_t command;   // 1=can grab, 0=cannot grab
  int8_t class_id;   // -1=no target, 0/1/2/3=meat/vegetable/fruit/drink
  uint8_t zone_id;   // 0=none, 1=A, 2=B, 3=C, 4=D, 5=E, 6=F
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

下位机到上位机：`GimbalToVision`，5 字节。

```cpp
struct __attribute__((packed)) GimbalToVision
{
  uint8_t head[2] = {'V', 'S'};
  uint8_t mode = static_cast<uint8_t>(VisionMode::IDLE);
  uint16_t crc16 = 0;
};
```

## Topics

| Topic | Type | Direction |
| --- | --- | --- |
| `/smarthome/object_target` | `robot_serial_comm/msg/ObjectTarget` | vision -> comm |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | nav/decision -> comm |
| `/smarthome/zone_id` | `std_msgs/msg/UInt8` | decision -> comm |
| `/vision_mode` | `std_msgs/msg/UInt8` | comm -> vision |
| `/robot_serial_comm/raw_tx_hex` | `std_msgs/msg/String` | debug |
| `/robot_serial_comm/raw_rx_hex` | `std_msgs/msg/String` | debug |

## Run

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py
```

常用参数：

```bash
ros2 launch robot_serial_comm robot_serial_comm.launch.py \
  serial_device:=/dev/ttyACM0 \
  baudrate:=115200 \
  fake_mode:=false
```
