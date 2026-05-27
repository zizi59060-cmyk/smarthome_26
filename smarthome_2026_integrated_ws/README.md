# smarthome_2026_integrated_ws

本工作空间用于把 `lf_sentry` 的单雷达导航链路、`smarthome_vision` 的视觉识别链路，以及比赛任务调度、上下位机通信统一到同一个 ROS 2 Humble 工程中。

> 本仓库是“集成层 + 通信层 + 任务层”的完整模板。导航和视觉源码通过 `third_party.repos` 拉取原始仓库，新增代码集中在：
>
> - `src/smarthome_common_interfaces`
> - `src/smarthome_comm`
> - `src/smarthome_task_manager`
> - `src/smarthome_bringup`
>
> 原则：所有串口/上下位机通信都进入 `smarthome_comm`，导航和视觉包不再直接碰底盘、机械臂、夹爪串口。

## 1. 总体任务

比赛任务抽象为以下流程：

1. 起点启动，自主建图或加载地图。
2. 依次导航到 B 区、C 区、D 区、E 区、F 区。
3. 在 D 区使用视觉检测桌面物品，获取类别与 3D 位姿。
4. 通过 `smarthome_comm` 向下位机发送机械臂抓取、夹爪闭合、搬运、放置指令。
5. 在 E 区结合二维码或类别区域信息完成分类放置。
6. 前往 F 区充电区，任务结束。

## 2. 推荐软件架构

```text
smarthome_2026_integrated_ws/
├── third_party.repos                 # 外部仓库导入清单
├── scripts/
│   ├── install_deps_ubuntu22_humble.sh
│   ├── import_sources.sh
│   ├── build_all.sh
│   └── run_mock_test.sh
├── docs/
│   ├── architecture.md
│   ├── protocol_table.md
│   └── vision_migration.md
└── src/
    ├── lf_sentry/                    # 由 vcs import 拉取
    ├── smarthome_vision/             # 由 vcs import 拉取
    ├── smarthome_common_interfaces/  # 自定义 msg/srv
    ├── smarthome_comm/               # 统一上下位机通信包
    ├── smarthome_task_manager/       # 比赛流程状态机
    └── smarthome_bringup/            # 总启动包
```

## 3. 环境配置：Ubuntu 22.04 + ROS 2 Humble

```bash
sudo apt update
sudo apt install -y curl gnupg lsb-release software-properties-common
sudo add-apt-repository universe

# 已安装 ROS 2 Humble 的机器可跳过 ROS 安装，只保留后面的依赖安装。
source /opt/ros/humble/setup.bash

sudo apt install -y \
  python3-colcon-common-extensions python3-vcstool python3-rosdep python3-serial \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-nav2-msgs \
  ros-humble-tf2-tools ros-humble-tf-transformations ros-humble-robot-localization \
  ros-humble-xacro ros-humble-robot-state-publisher ros-humble-joint-state-publisher \
  ros-humble-image-transport ros-humble-cv-bridge ros-humble-camera-info-manager \
  ros-humble-image-tools ros-humble-diagnostic-msgs

sudo rosdep init 2>/dev/null || true
rosdep update
```

也可以直接执行：

```bash
cd smarthome_2026_integrated_ws
bash scripts/install_deps_ubuntu22_humble.sh
```

## 4. 导入导航与视觉原工程

```bash
cd smarthome_2026_integrated_ws
bash scripts/import_sources.sh
```

如果网络不能直连 GitHub，先自行把以下两个仓库下载或复制到 `src/` 下：

```text
src/lf_sentry
src/smarthome_vision
```

## 5. 编译整个代码库

```bash
cd smarthome_2026_integrated_ws
bash scripts/build_all.sh
```

脚本内部执行的是：

```bash
source /opt/ros/humble/setup.bash
rosdep install -r --from-paths src --ignore-src --rosdistro humble -y
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

如果第三方包依赖过多，先编译新增集成层：

```bash
colcon build --symlink-install \
  --packages-up-to smarthome_bringup smarthome_task_manager smarthome_comm smarthome_common_interfaces
```

## 6. 单雷达导航使用方式

本工程按单个 Livox MID360/单雷达链路组织，不使用多机器人、多雷达命名空间扩展。实车建议启动：

```bash
source install/setup.bash
ros2 launch smarthome_bringup online_competition.launch.py \
  namespace:=smarthome \
  world:=smarthome_2026 \
  slam:=False \
  use_robot_state_pub:=True \
  use_rviz:=True \
  fake_comm:=False \
  serial_device:=/dev/ttyACM0
```

建图时：

```bash
ros2 launch smarthome_bringup online_competition.launch.py \
  namespace:=smarthome \
  slam:=True \
  use_robot_state_pub:=True \
  fake_comm:=True
```

## 7. 上下位机通信集中化原则

`smarthome_comm` 是唯一允许打开串口的 ROS 2 功能包。其它包只能通过 ROS topic/service/action 与它交互。

默认通信链路：

```text
Nav2 /cmd_vel ───────────────┐
Vision /smarthome/object_target ─┐
TaskManager arm/gripper service ─┼──> smarthome_comm ── Serial/UART/CAN-bridge ── 下位机
Lower MCU status/ack ────────────┘
```

核心接口：

| ROS 接口 | 类型 | 方向 | 含义 |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | Nav2 -> comm | 底盘速度指令，映射到下位机 `CMD_CHASSIS_VEL` |
| `/smarthome/object_target` | `smarthome_common_interfaces/ObjectTarget` | Vision -> comm | 视觉目标类别、位姿、置信度 |
| `/smarthome/comm/arm_command` | `smarthome_common_interfaces/srv/ArmCommand` | Task -> comm | 机械臂 HOME/PICK/PLACE/STOP |
| `/smarthome/comm/gripper` | `example_interfaces/srv/SetBool` | Task -> comm | `true` 打开夹爪，`false` 闭合夹爪 |
| `/smarthome/lower_state` | `smarthome_common_interfaces/LowerState` | comm -> ROS | 下位机状态、急停、电池、错误码 |
| `/smarthome/comm/raw_rx` | `smarthome_common_interfaces/CommFrame` | comm -> ROS | 调试用原始接收帧 |
| `/smarthome/comm/raw_tx` | `smarthome_common_interfaces/CommFrame` | comm -> ROS | 调试用原始发送帧 |

详细协议见 `docs/protocol_table.md` 和 `src/smarthome_comm/README.md`。

## 8. 视觉包迁移要求

`smarthome_vision` 原 README 说明视觉包内部保留 `gimbal` 串口层并发送 `class_id + x + y + z`。本工程的集成原则是把这部分串口发送迁移到 `smarthome_comm`。因此视觉节点应只发布目标，不直接打开串口。

推荐做法：

1. 保留 `Detector`、`PoseSolver`、TensorRT 推理部分。
2. 移除或禁用 `GimbalBridge` 的串口写入。
3. 将检测结果发布为 `/smarthome/object_target`。
4. `smarthome_comm` 订阅该 topic 后统一打包发送到下位机。

详细迁移说明见 `docs/vision_migration.md`。

## 9. 任务流程配置

`src/smarthome_task_manager/config/waypoints.yaml` 中给出了 A/B/C/D/E/F 示例点位。你需要根据实测地图坐标修改：

```yaml
zones:
  B: {x: 3.6, y: -1.6, yaw: 0.0}
  C: {x: 0.8, y: -3.2, yaw: 1.57}
  D: {x: 2.55, y: -0.35, yaw: 1.57}
  E: {x: 1.55, y:  1.80, yaw: 3.14}
  F: {x: 0.35, y:  3.35, yaw: 3.14}
```

启动任务状态机：

```bash
ros2 launch smarthome_task_manager mission.launch.py waypoint_file:=src/smarthome_task_manager/config/waypoints.yaml
ros2 service call /smarthome/task/start example_interfaces/srv/Trigger {}
```

## 10. 调试建议

先用 fake 通信跑通 ROS 图：

```bash
ros2 launch smarthome_bringup online_competition.launch.py fake_comm:=True launch_navigation:=False launch_vision:=False
ros2 topic echo /smarthome/lower_state
ros2 service call /smarthome/comm/gripper example_interfaces/srv/SetBool "{data: false}"
```

确认串口后再切换：

```bash
ros2 launch smarthome_comm comm.launch.py fake_mode:=False serial_device:=/dev/ttyACM0 baudrate:=115200
```

## 11. 需要你在实车上补齐的内容

1. 根据真实建图结果更新 `waypoints.yaml`。
2. 根据你的下位机协议调整 `smarthome_comm/config/protocol.yaml` 的 `cmd_id` 或载荷格式。
3. 将视觉模型 engine 路径写入 `smarthome_bringup/config/vision_override.yaml` 或原视觉包配置。
4. 如果下位机已经有既有协议，保留 ROS 接口不变，只替换 `smarthome_comm/smarthome_comm/protocol.py` 中的 pack/unpack。
