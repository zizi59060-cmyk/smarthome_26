# pb2025_nav_bringup

`pb2025_nav_bringup` 是当前智能家居项目使用的导航启动包。它负责启动实车或仿真的 Nav2、定位、雷达、手柄遥控和 RViz。

## 与当前项目的关系

```text
pb2025_nav_bringup --> Nav2/controller --> /cmd_vel --> robot_serial_comm
```

本包不处理视觉目标、不打开下位机串口，也不拼通信协议。它只需要稳定发布 `/cmd_vel`，通信节点会把速度写入 `VisionToGimbal.vx/vy/wz`。

## 实车启动

```bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
  use_robot_state_pub:=True \
  use_rviz:=True
```

常用参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `namespace` | 空 | ROS namespace |
| `slam` | `False` | 是否启用 SLAM |
| `world` | `rmul_2024` | 地图和点云文件名基础值 |
| `map` | `map/reality/<world>.yaml` | 地图 yaml |
| `prior_pcd_file` | `pcd/reality/<world>.pcd` | 重定位用先验点云 |
| `use_sim_time` | `False` | 是否使用仿真时间 |
| `params_file` | `config/reality/nav2_params.yaml` | Nav2 参数文件 |
| `autostart` | `true` | 是否自动激活 Nav2 生命周期节点 |
| `use_composition` | `True` | 是否使用组件容器 |
| `use_respawn` | `False` | 节点崩溃后是否重启 |
| `use_robot_state_pub` | `False` | 是否启动 robot_state_publisher |
| `use_rviz` | `True` | 是否启动 RViz |

当前智能家居项目通常把 `use_robot_state_pub` 设为 `True`，因为不默认启动 `standard_robot_pp_ros2`。

## 仿真启动

```bash
ros2 launch pb2025_nav_bringup rm_navigation_simulation_launch.py
```

多机仿真：

```bash
ros2 launch pb2025_nav_bringup rm_multi_navigation_simulation_launch.py
```

## 编译

```bash
cd ~/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to pb2025_nav_bringup
source install/setup.bash
```

## 修改方式

| 需求 | 文件 |
| --- | --- |
| 改实车导航启动流程 | `launch/rm_navigation_reality_launch.py` |
| 改仿真启动流程 | `launch/rm_navigation_simulation_launch.py` |
| 改 Nav2 节点组合 | `launch/bringup_launch.py` |
| 改定位 | `launch/localization_launch.py` |
| 改路径规划和控制参数 | `config/reality/nav2_params.yaml` |
| 改雷达配置 | `config/reality/mid360_user_config.json` |
| 改 RViz 默认视图 | `rviz/nav2_default_view.rviz` |

导航调通后检查 `/cmd_vel`：

```bash
ros2 topic echo /cmd_vel
```

只要这里有速度，`robot_serial_comm` 就能把速度带到串口发送包里。
