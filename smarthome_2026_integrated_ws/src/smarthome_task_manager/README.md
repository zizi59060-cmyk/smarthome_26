# smarthome_task_manager

这个包是早期任务状态机模板，当前实车默认流程不再启动它。

新的默认决策入口是：

```bash
ros2 launch pb2025_sentry_behavior pb2025_sentry_behavior_launch.py
```

该命令默认启动 `smart_picking_manager`，通过 `/smarthome/zone_id` 给通信包提供 A-F 点位。旧任务状态机里保留的机械臂/夹爪服务调用只作为历史模板，不参与当前 `robot_serial_comm` 协议。
