# smarthome_task_manager

比赛流程状态机。它不直接控制串口，也不直接操作视觉模型，而是通过 Nav2 action、`smarthome_comm` 服务和 `/smarthome/object_target` 话题串联任务。

## 流程

```text
MISSION_BEGIN
  -> NAV_TO_B
  -> NAV_TO_C
  -> NAV_TO_D
  -> WAIT_OBJECT_TARGET
  -> ARM PICK + GRIPPER CLOSE
  -> NAV_TO_E
  -> ARM PLACE + GRIPPER OPEN
  -> NAV_TO_F
MISSION_DONE
```

## 配置

修改 `config/waypoints.yaml` 中 B/C/D/E/F 的 map 坐标。

字段含义：

| 字段 | 含义 |
|---|---|
| `frame_id` | 导航目标坐标系，通常为 `map` |
| `nav_action_name` | Nav2 action 名称，单机默认 `/navigate_to_pose`；有 namespace 时改为 `/smarthome/navigate_to_pose` |
| `zones.B/C/D/E/F` | 比赛区域导航目标点 |
| `mission.visit_zones` | 抓取前需要到达的区域序列 |
| `mission.pick_count` | 尝试抓取物品数量 |
| `mission.place_zone` | 分类放置区，默认 E |
| `mission.finish_zone` | 结束/充电区，默认 F |

## 启动

```bash
ros2 launch smarthome_task_manager mission.launch.py
ros2 service call /smarthome/task/start example_interfaces/srv/Trigger {}
```
