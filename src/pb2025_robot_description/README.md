# pb2025_robot_description

`pb2025_robot_description` 提供机器人 URDF/SDF/XMacro 描述。当前智能家居链路中，它主要服务于导航 TF 和 RViz 可视化。

## 链路位置

```text
pb2025_nav_bringup --use_robot_state_pub:=True--> robot_state_publisher
robot_state_publisher --> /tf, /tf_static --> Nav2 / RViz
```

如果系统中已有其它节点发布完整机器人 TF，可以在导航启动时把 `use_robot_state_pub` 设为 `False`。

## 启动

单独查看机器人描述：

```bash
ros2 launch pb2025_robot_description robot_description_launch.py
```

当前项目中通常由导航启动间接使用：

```bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
  use_robot_state_pub:=True \
  use_rviz:=True
```

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to pb2025_robot_description
source install/setup.bash
```

## 修改方式

| 需求 | 目录或文件 |
| --- | --- |
| 改机器人模型 | `resource/xmacro/` |
| 改传感器安装位置 | `resource/xmacro/` 中对应 xmacro |
| 改启动或生成 URDF 的参数 | `launch/` |
| 改 RViz 观察模型 | 使用 `robot_description_launch.py` 启动后在 RViz 检查 |

改模型后重点检查 TF 树，确保导航需要的 `map`、`odom`、`chassis`、雷达和相机坐标系没有断链。
