#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch smarthome_bringup online_competition.launch.py \
  launch_navigation:=False \
  launch_vision:=False \
  fake_comm:=True \
  use_rviz:=False
