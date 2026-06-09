#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/humble/setup.bash
rosdep install -r --from-paths src --ignore-src --rosdistro humble -y
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

echo "[OK] build finished. Run: source install/setup.bash"
