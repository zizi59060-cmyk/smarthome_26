# Vision Migration

视觉串口迁移已完成：

- `vision_node` 不再打开下位机串口。
- 旧的 `GimbalBridge` 源文件已删除。
- 视觉节点订阅 `/vision_mode`，由下位机决定 `IDLE / DETECT_OBJECT / DETECT_QR`。
- 视觉节点发布 `/smarthome/object_target`，通信节点统一打包发送。
- `smarthome_vision/launch/vision.launch.py` 默认同时包含 `robot_serial_comm.launch.py`。

调试视觉时如需绕过下位机模式，可以在参数中设置：

```yaml
use_test_mode: true
test_mode: 1
```

实车运行时应保持：

```yaml
use_test_mode: false
```
