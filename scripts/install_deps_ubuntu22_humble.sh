#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y \
  git curl gnupg lsb-release software-properties-common build-essential cmake \
  python3-colcon-common-extensions python3-vcstool python3-rosdep python3-serial \
  python3-pip python3-yaml \
  libeigen3-dev libomp-dev \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-nav2-msgs \
  ros-humble-tf2-tools ros-humble-tf-transformations ros-humble-robot-localization \
  ros-humble-xacro ros-humble-robot-state-publisher ros-humble-joint-state-publisher \
  ros-humble-image-transport ros-humble-cv-bridge ros-humble-camera-info-manager \
  ros-humble-image-tools ros-humble-diagnostic-msgs ros-humble-example-interfaces

sudo rosdep init 2>/dev/null || true
rosdep update

echo "[OK] Base dependencies installed. TensorRT / CUDA / OpenCV CUDA should match your smarthome_vision build machine."
