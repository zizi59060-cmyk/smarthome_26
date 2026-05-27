# smarthome_vision 通信迁移说明

## 1. 问题

原视觉包包含 `gimbal_bridge` 串口通信层，README 中说明它会发送 `class_id + x + y + z`。如果继续保留这条串口链路，同时 `smarthome_comm` 也打开下位机串口，会产生两个问题：

1. 串口设备被多个节点争用。
2. 视觉包与下位机协议强耦合，不利于任务调度和调试。

## 2. 目标

视觉包只负责：

- 相机图像输入。
- TensorRT 检测。
- 物品/二维码类别输出。
- 目标 3D 位姿估计。
- 发布 ROS 目标消息。

串口发送统一由 `smarthome_comm` 负责。

## 3. 推荐修改方式

在 `smarthome_vision_node` 中保留原先的检测结果结构，将串口发送替换为发布：

```cpp
// 伪代码，仅说明迁移位置。
smarthome_common_interfaces::msg::ObjectTarget msg;
msg.header.stamp = now();
msg.class_id = result.class_id;
msg.score = result.score;
msg.source = smarthome_common_interfaces::msg::ObjectTarget::SOURCE_OBJECT;
msg.pose.header.frame_id = "camera_link";  // 或已转换后的 base_link/map
msg.pose.pose.position.x = result.x;
msg.pose.pose.position.y = result.y;
msg.pose.pose.position.z = result.z;
msg.pose.pose.orientation.w = 1.0;
target_pub_->publish(msg);
```

然后删除或用参数禁用：

```cpp
gimbal_bridge_->send(...);
```

## 4. 如果暂时不改 C++ 视觉包

可以先让视觉包输出 `geometry_msgs/PoseStamped`，再使用：

```bash
ros2 run smarthome_comm vision_pose_adapter \
  --ros-args \
  -p input_pose_topic:=/vision/target_pose \
  -p output_target_topic:=/smarthome/object_target \
  -p class_id:=0
```

这只能传一个固定类别，适合联调，不适合最终比赛。

## 5. 坐标系建议

- 视觉原始 PnP 通常在 `camera_link` 下。
- 抓取前最好转换到机械臂基座 `arm_base_link`。
- 如果目标用于导航或桌面区域定位，可再转换到 `base_link` 或 `map`。
- 串口中 `VISION_TARGET` 的 x/y/z 必须在 README 或下位机协议中明确对应坐标系。
