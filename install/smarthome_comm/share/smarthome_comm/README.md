# smarthome_comm：统一上下位机通信功能包

本包是工程里唯一允许直接访问串口的包。导航、视觉、任务状态机均不直接访问 `/dev/tty*`，只通过 ROS 接口向本包发命令。

## 1. 节点

```bash
ros2 launch smarthome_comm comm.launch.py fake_mode:=True
ros2 launch smarthome_comm comm.launch.py fake_mode:=False serial_device:=/dev/ttyACM0 baudrate:=115200
```

节点名：`/smarthome_comm_node`

## 2. ROS 参数

| 参数 | 默认值 | 含义 |
|---|---:|---|
| `serial_device` | `/dev/ttyACM0` | 下位机串口设备路径 |
| `baudrate` | `115200` | 串口波特率 |
| `fake_mode` | `true` | 是否关闭真实串口，发布模拟下位机状态 |
| `read_hz` | `200.0` | 串口读轮询频率 |
| `heartbeat_hz` | `2.0` | 上位机心跳发送频率 |
| `cmd_vel_topic` | `/cmd_vel` | 订阅的底盘速度话题 |
| `object_target_topic` | `/smarthome/object_target` | 订阅的视觉目标话题 |
| `lower_state_topic` | `/smarthome/lower_state` | 发布下位机状态的话题 |
| `raw_rx_topic` | `/smarthome/comm/raw_rx` | 发布原始接收帧的话题 |
| `raw_tx_topic` | `/smarthome/comm/raw_tx` | 发布原始发送帧的话题 |
| `enable_cmd_vel` | `true` | 是否启用底盘速度转发 |
| `enable_object_target` | `true` | 是否启用视觉目标转发 |

## 3. 串口帧格式

所有整数小端序。

| 字段 | 类型 | 字节数 | 含义 |
|---|---:|---:|---|
| `magic` | `uint16` | 2 | 固定 `0x5AA5`，实际字节序为 `A5 5A` |
| `version` | `uint8` | 1 | 协议版本，当前为 `1` |
| `seq` | `uint8` | 1 | 上位机递增序号，0~255 循环 |
| `cmd_id` | `uint16` | 2 | 命令 ID |
| `payload_len` | `uint16` | 2 | 载荷长度，最大 512 字节 |
| `payload` | `uint8[]` | N | 命令载荷 |
| `crc16` | `uint16` | 2 | Modbus CRC16，覆盖 header + payload |

## 4. 命令表

| cmd_id | 名称 | 方向 | payload | 含义 |
|---:|---|---|---|---|
| `0x0001` | `HEARTBEAT_TX` | 上位机->下位机 | `uint32 time_ms` | 上位机心跳 |
| `0x0101` | `CHASSIS_VEL` | 上位机->下位机 | `float vx, float vy, float wz` | 底盘速度，单位 m/s、m/s、rad/s |
| `0x0201` | `VISION_TARGET` | 上位机->下位机 | `uint8 class_id, uint8 source, float x, float y, float z, float score` | 视觉目标结果，坐标单位 m |
| `0x0301` | `GRIPPER` | 上位机->下位机 | `uint8 open` | `1` 打开夹爪，`0` 闭合夹爪 |
| `0x0302` | `ARM_COMMAND` | 上位机->下位机 | `uint8 command, uint8 class_id, float x,y,z,qx,qy,qz,qw` | 机械臂动作命令和目标位姿 |
| `0x0401` | `ESTOP` | 上位机->下位机 | `uint8 estop` | `1` 急停，`0` 解除急停 |
| `0x0501` | `NAV_EVENT` | 上位机->下位机 | `uint8 event_code, uint8 zone_id` | 导航到达或任务事件 |
| `0x8001` | `HEARTBEAT_RX` | 下位机->上位机 | 自定义 | 下位机心跳 |
| `0x8002` | `LOWER_STATE` | 下位机->上位机 | `uint8 mode, uint8 estop, float battery_v, float battery_i, float temp, uint16 error, uint32 uptime_ms` | 下位机状态 |
| `0x8003` | `ARM_STATUS` | 下位机->上位机 | 自定义 | 机械臂状态 |
| `0x80FF` | `ACK` | 下位机->上位机 | `uint16 ack_cmd, uint8 ok, uint8 reason` | 对上位机命令的确认 |

## 5. 类别编号建议

| class_id | 类别 | 说明 |
|---:|---|---|
| `0` | 肉类 | 对应比赛图示的肉类物品 |
| `1` | 蔬菜 | 对应比赛图示的蔬菜物品 |
| `2` | 水果 | 对应比赛图示的水果物品 |
| `3` | 预留/其它 | 用于新增类别或兜底 |

## 6. 对接下位机

下位机只需要实现：

1. 按帧格式解析 `magic/version/seq/cmd_id/payload_len/payload/crc16`。
2. 处理 `CHASSIS_VEL`、`GRIPPER`、`ARM_COMMAND`、`ESTOP`。
3. 周期发送 `LOWER_STATE`。
4. 对每条关键命令返回 `ACK`。

如果你们已有历史协议，不要改 ROS 接口；只改 `smarthome_comm/protocol.py` 的 pack/unpack，使上层代码保持不变。
