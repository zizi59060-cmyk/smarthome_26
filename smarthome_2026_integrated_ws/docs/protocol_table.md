# 上下位机通信协议说明

## 1. 设计目标

比赛工程中会同时存在导航、视觉、机械臂、夹爪、底盘等模块。如果每个模块都直接打开串口，会出现资源竞争、协议耦合、调试困难。因此本工程规定：

> `smarthome_comm` 是唯一串口通信功能包。其它功能包只通过 ROS topic/service/action 与它交互。

## 2. 坐标与单位约定

| 项 | 约定 |
|---|---|
| 线速度 | m/s |
| 角速度 | rad/s |
| 位置 | m |
| 四元数 | x, y, z, w |
| 角度 | ROS 内部全部用 rad |
| 图像目标类别 | `class_id`，由视觉模型输出并映射到比赛类别 |
| 下位机字节序 | little-endian |

## 3. 帧格式

| 偏移 | 字段 | 类型 | 含义 |
|---:|---|---|---|
| 0 | `magic[0]` | uint8 | 固定 `0xA5` |
| 1 | `magic[1]` | uint8 | 固定 `0x5A` |
| 2 | `version` | uint8 | 当前为 `1` |
| 3 | `seq` | uint8 | 帧序号 |
| 4 | `cmd_id` | uint16 | 命令 ID，小端序 |
| 6 | `payload_len` | uint16 | 载荷长度，小端序 |
| 8 | `payload` | uint8[] | 载荷 |
| 8+N | `crc16` | uint16 | CRC16-Modbus，小端序 |

CRC 覆盖 `magic` 到 `payload` 的所有字节，不覆盖 CRC 自身。

## 4. 命令载荷定义

| 命令 | cmd_id | 方向 | 载荷 | 说明 |
|---|---:|---|---|---|
| HEARTBEAT_TX | 0x0001 | 上->下 | `uint32 time_ms` | 上位机心跳 |
| CHASSIS_VEL | 0x0101 | 上->下 | `float vx, float vy, float wz` | 底盘速度控制 |
| VISION_TARGET | 0x0201 | 上->下 | `uint8 class_id, uint8 source, float x, y, z, score` | 视觉识别结果转发 |
| GRIPPER | 0x0301 | 上->下 | `uint8 open` | 夹爪控制 |
| ARM_COMMAND | 0x0302 | 上->下 | `uint8 command, uint8 class_id, float x,y,z,qx,qy,qz,qw` | 机械臂控制 |
| ESTOP | 0x0401 | 上->下 | `uint8 estop` | 急停/解除急停 |
| NAV_EVENT | 0x0501 | 上->下 | `uint8 event_code, uint8 zone_id` | 导航事件通知 |
| HEARTBEAT_RX | 0x8001 | 下->上 | 自定义 | 下位机心跳 |
| LOWER_STATE | 0x8002 | 下->上 | `uint8 mode, uint8 estop, float battery_v, float battery_i, float temp, uint16 error, uint32 uptime_ms` | 下位机状态 |
| ARM_STATUS | 0x8003 | 下->上 | 自定义 | 机械臂状态 |
| ACK | 0x80FF | 下->上 | `uint16 ack_cmd, uint8 ok, uint8 reason` | 命令应答 |

## 5. ARM_COMMAND.command

| 值 | 名称 | 含义 |
|---:|---|---|
| 0 | HOME | 回到安全初始位姿 |
| 1 | PICK | 根据目标位姿执行抓取 |
| 2 | PLACE | 执行放置 |
| 3 | STOP | 停止当前机械臂动作 |
| 4 | SCAN | 执行扫描动作 |

## 6. 建议 ACK reason

| reason | 含义 |
|---:|---|
| 0 | OK |
| 1 | CRC 错误 |
| 2 | 未知命令 |
| 3 | payload 长度错误 |
| 4 | 参数越界 |
| 5 | 当前状态拒绝执行 |
| 6 | 急停状态拒绝执行 |

## 7. 与 ROS 接口对应关系

| ROS 输入 | 串口命令 |
|---|---|
| `/cmd_vel` | `CHASSIS_VEL` |
| `/smarthome/object_target` | `VISION_TARGET` |
| `/smarthome/comm/gripper` | `GRIPPER` |
| `/smarthome/comm/arm_command` | `ARM_COMMAND` |
| `/smarthome/comm/set_estop` | `ESTOP` |

| 串口输入 | ROS 输出 |
|---|---|
| `LOWER_STATE` | `/smarthome/lower_state` |
| 任意接收帧 | `/smarthome/comm/raw_rx` |
| 任意发送帧 | `/smarthome/comm/raw_tx` |
