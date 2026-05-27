# smarthome_common_interfaces

公共接口包。导航、视觉、通信、任务状态机之间只通过本包定义的 msg/srv 交互。

## 消息

- `CommFrame`：通信层调试帧，记录 cmd_id、方向、序号、载荷、CRC 状态。
- `LowerState`：下位机状态，含急停、电池、温度、错误码、收发计数。
- `ObjectTarget`：视觉目标，含类别、3D 位姿、置信度、来源。

## 服务

- `ArmCommand`：机械臂动作命令，支持 HOME/PICK/PLACE/STOP/SCAN。
