# pb2025_sentry_behavior

`pb2025_sentry_behavior` 是当前项目的决策包。`zhou` 分支默认启动轻量的 `smart_picking_manager`，不默认启动旧 BehaviorTree server/client。

默认启动参数：

```text
enable_smart_picking=true
enable_legacy_bt=false
```

## 链路位置

```text
smarthome_vision --> /smarthome/object_target --> smart_picking_manager
robot_serial_comm --> /vision_mode -------------> smart_picking_manager
operator ---------> /smarthome/zone_name -------> smart_picking_manager
smart_picking_manager --> /smarthome/zone_id ---> robot_serial_comm --> 下位机
```

`smart_picking_manager` 当前主要负责把 A-F 点位转换成下位机需要的 `zone_id`，并发布状态方便调试。

## 启动

默认启动当前智能抓取决策：

```bash
ros2 launch pb2025_sentry_behavior pb2025_sentry_behavior_launch.py
```

临时切回旧 BehaviorTree：

```bash
ros2 launch pb2025_sentry_behavior pb2025_sentry_behavior_launch.py \
  enable_smart_picking:=false \
  enable_legacy_bt:=true
```

## smart_picking_manager 接口

| Topic/Service | Type | 方向 | 说明 |
| --- | --- | --- | --- |
| `/smarthome/object_target` | `robot_serial_comm/msg/ObjectTarget` | sub | 视觉目标 |
| `/vision_mode` | `std_msgs/msg/UInt8` | sub | 下位机视觉模式 |
| `/smarthome/zone_name` | `std_msgs/msg/String` | sub | 手动设置点位，支持 `A` 到 `F` 和 `NONE` |
| `/smarthome/zone_id` | `std_msgs/msg/UInt8` | pub | 发给通信节点的数字点位 |
| `/smarthome/smart_picking/state` | `std_msgs/msg/String` | pub | 当前运行、点位、模式和目标状态 |
| `/smarthome/smart_picking/start` | `example_interfaces/srv/Trigger` | srv | 开始发布点位 |
| `/smarthome/smart_picking/stop` | `example_interfaces/srv/Trigger` | srv | 停止发布点位，输出 `zone_id=0` |

点位映射：

| 名称 | zone_id |
| --- | --- |
| `NONE` | `0` |
| `A` | `1` |
| `B` | `2` |
| `C` | `3` |
| `D` | `4` |
| `E` | `5` |
| `F` | `6` |

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `auto_start` | `true` | 启动后是否立即发布点位 |
| `target_topic` | `/smarthome/object_target` | 视觉目标输入 |
| `vision_mode_topic` | `/vision_mode` | 视觉模式输入 |
| `zone_id_topic` | `/smarthome/zone_id` | 点位数字输出 |
| `zone_name_topic` | `/smarthome/zone_name` | 点位名称输入 |
| `state_topic` | `/smarthome/smart_picking/state` | 状态输出 |
| `initial_zone` | `NONE` | 初始点位 |
| `publish_hz` | `10.0` | 点位发布频率 |

## 常用调试

手动切点位：

```bash
ros2 topic pub --once /smarthome/zone_name std_msgs/msg/String "{data: C}"
```

查看当前状态：

```bash
ros2 topic echo /smarthome/smart_picking/state
```

停止和恢复点位发布：

```bash
ros2 service call /smarthome/smart_picking/stop example_interfaces/srv/Trigger {}
ros2 service call /smarthome/smart_picking/start example_interfaces/srv/Trigger {}
```

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to pb2025_sentry_behavior
source install/setup.bash
```

## 修改方式

| 需求 | 文件 |
| --- | --- |
| 改默认启动 smart manager 或旧 BT | `launch/pb2025_sentry_behavior_launch.py` |
| 改点位映射和当前轻量决策 | `scripts/smart_picking_manager.py` |
| 改旧 BehaviorTree 参数 | `params/sentry_behavior.yaml` |
| 改旧 BT XML | `behavior_trees/` |
| 改 C++ BT 插件 | `src/` 和 `include/` |

当前智能家居链路优先改 `smart_picking_manager.py`。只有明确要回到旧哨兵行为树时，才需要改旧 BT server/client。
