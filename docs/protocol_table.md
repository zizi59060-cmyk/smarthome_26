# Serial Protocol

CRC 使用 CRC16 Modbus，小端序，覆盖除 `crc16` 之外的所有字段。

## VisionToGimbal

上位机到下位机，31 字节。

| Offset | Type | Name | Meaning |
| --- | --- | --- | --- |
| 0 | `uint8[2]` | `head` | `S P` |
| 2 | `uint8` | `command` | `1` 可以抓取，`0` 不能抓取 |
| 3 | `int8` | `class_id` | `-1` 无目标，`0/1/2/3` 肉/蔬菜/水果/饮料 |
| 4 | `uint8` | `zone_id` | `0` none, `1` A, `2` B, `3` C, `4` D, `5` E, `6` F |
| 5 | `float` | `x` | 目标相对相机 x |
| 9 | `float` | `y` | 目标相对相机 y |
| 13 | `float` | `z` | 目标相对相机 z |
| 17 | `float` | `vx` | 底盘 x 速度 |
| 21 | `float` | `vy` | 底盘 y 速度 |
| 25 | `float` | `wz` | 底盘角速度 |
| 29 | `uint16` | `crc16` | CRC16 Modbus |

## GimbalToVision

下位机到上位机，5 字节。

| Offset | Type | Name | Meaning |
| --- | --- | --- | --- |
| 0 | `uint8[2]` | `head` | `V S` |
| 2 | `uint8` | `mode` | `0` IDLE, `1` DETECT_OBJECT, `2` DETECT_QR |
| 3 | `uint16` | `crc16` | CRC16 Modbus |

## ROS Mapping

| ROS input | Packet fields |
| --- | --- |
| `/smarthome/object_target` | `command`, `class_id`, `x`, `y`, `z` |
| `/cmd_vel` | `vx`, `vy`, `wz` |
| `/smarthome/zone_id` | `zone_id` |
| lower serial packet | `/vision_mode` |
