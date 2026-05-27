from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Dict, Optional

import yaml
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from example_interfaces.srv import Trigger, SetBool
from nav2_msgs.action import NavigateToPose

from smarthome_common_interfaces.msg import ObjectTarget
from smarthome_common_interfaces.srv import ArmCommand


def yaw_to_quat(yaw: float):
    qz = math.sin(yaw * 0.5)
    qw = math.cos(yaw * 0.5)
    return (0.0, 0.0, qz, qw)


class MissionNode(Node):
    def __init__(self) -> None:
        super().__init__('smarthome_mission_node')
        self.declare_parameter('waypoint_file', '')
        self.declare_parameter('auto_start', False)
        self.declare_parameter('object_target_topic', '/smarthome/object_target')
        self.declare_parameter('state_topic', '/smarthome/task/state')
        self.declare_parameter('arm_service', '/smarthome/comm/arm_command')
        self.declare_parameter('gripper_service', '/smarthome/comm/gripper')

        self.cfg = self.load_config(str(self.get_parameter('waypoint_file').value))
        self.frame_id = self.cfg.get('frame_id', 'map')
        self.nav_action_name = self.cfg.get('nav_action_name', '/navigate_to_pose')
        self.nav_timeout_sec = float(self.cfg.get('nav_timeout_sec', 120.0))
        self.wait_target_timeout_sec = float(self.cfg.get('wait_target_timeout_sec', 8.0))
        self.pick_timeout_sec = float(self.cfg.get('pick_timeout_sec', 20.0))
        self.place_timeout_sec = float(self.cfg.get('place_timeout_sec', 20.0))

        self.state_pub = self.create_publisher(String, str(self.get_parameter('state_topic').value), 10)
        self.target_sub = self.create_subscription(
            ObjectTarget,
            str(self.get_parameter('object_target_topic').value),
            self.on_target,
            10,
        )
        self.start_srv = self.create_service(Trigger, '/smarthome/task/start', self.on_start)
        self.stop_srv = self.create_service(Trigger, '/smarthome/task/stop', self.on_stop)

        self.nav_client = ActionClient(self, NavigateToPose, self.nav_action_name)
        self.arm_client = self.create_client(ArmCommand, str(self.get_parameter('arm_service').value))
        self.gripper_client = self.create_client(SetBool, str(self.get_parameter('gripper_service').value))

        self.latest_target: Optional[ObjectTarget] = None
        self.running = False

        if bool(self.get_parameter('auto_start').value):
            self.create_timer(2.0, self._auto_start_once)

    def load_config(self, filename: str) -> dict:
        if filename:
            p = Path(filename).expanduser()
            if p.exists():
                return yaml.safe_load(p.read_text(encoding='utf-8'))
            self.get_logger().warn(f'waypoint_file not found: {p}; using defaults')
        return {
            'frame_id': 'map',
            'nav_action_name': '/navigate_to_pose',
            'zones': {},
            'mission': {'visit_zones': ['B', 'C', 'D'], 'pick_count': 4, 'place_zone': 'E', 'finish_zone': 'F'},
        }

    def _auto_start_once(self) -> None:
        if not self.running:
            self.running = True
            self.run_mission()

    def publish_state(self, text: str) -> None:
        msg = String()
        msg.data = text
        self.state_pub.publish(msg)
        self.get_logger().info(text)

    def on_target(self, msg: ObjectTarget) -> None:
        self.latest_target = msg

    def on_start(self, request, response):
        if self.running:
            response.success = False
            response.message = 'mission already running'
            return response
        self.running = True
        # Run in timer callback to avoid blocking service callback return path too long.
        self.create_timer(0.1, self._start_timer_cb)
        response.success = True
        response.message = 'mission started'
        return response

    def _start_timer_cb(self):
        # one-shot behavior: destroy the timer that invoked us by scanning timers is not public;
        # guard with running flag is enough for this template.
        if getattr(self, '_mission_entered', False):
            return
        self._mission_entered = True
        self.run_mission()

    def on_stop(self, request, response):
        self.running = False
        response.success = True
        response.message = 'mission stop requested'
        self.publish_state('STOP_REQUESTED')
        return response

    def make_pose(self, zone_name: str) -> PoseStamped:
        zone = self.cfg.get('zones', {}).get(zone_name)
        if zone is None:
            raise KeyError(f'zone {zone_name} not in waypoint config')
        pose = PoseStamped()
        pose.header.frame_id = self.frame_id
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(zone['x'])
        pose.pose.position.y = float(zone['y'])
        pose.pose.position.z = 0.0
        q = yaw_to_quat(float(zone.get('yaw', 0.0)))
        pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z, pose.pose.orientation.w = q
        return pose

    def go_to_zone(self, zone_name: str) -> bool:
        self.publish_state(f'NAV_TO_{zone_name}')
        if not self.nav_client.wait_for_server(timeout_sec=10.0):
            self.publish_state(f'NAV_SERVER_TIMEOUT_{zone_name}')
            return False
        goal = NavigateToPose.Goal()
        goal.pose = self.make_pose(zone_name)
        send_future = self.nav_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=5.0)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.publish_state(f'NAV_GOAL_REJECTED_{zone_name}')
            return False
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=self.nav_timeout_sec)
        if not result_future.done():
            self.publish_state(f'NAV_TIMEOUT_{zone_name}')
            return False
        result = result_future.result()
        status = getattr(result, 'status', None)
        self.publish_state(f'NAV_DONE_{zone_name}_STATUS_{status}')
        return True

    def wait_for_target(self, timeout_sec: float) -> Optional[ObjectTarget]:
        self.latest_target = None
        self.publish_state('WAIT_OBJECT_TARGET')
        t0 = time.monotonic()
        while self.running and time.monotonic() - t0 < timeout_sec:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.latest_target is not None:
                self.publish_state(f'TARGET_FOUND_CLASS_{self.latest_target.class_id}')
                return self.latest_target
        self.publish_state('TARGET_TIMEOUT')
        return None

    def call_gripper(self, open_gripper: bool, timeout_sec: float = 3.0) -> bool:
        if not self.gripper_client.wait_for_service(timeout_sec=timeout_sec):
            self.publish_state('GRIPPER_SERVICE_TIMEOUT')
            return False
        req = SetBool.Request()
        req.data = bool(open_gripper)
        fut = self.gripper_client.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=timeout_sec)
        return fut.done() and bool(fut.result().success)

    def call_arm(self, command: int, target: Optional[ObjectTarget], timeout_sec: float) -> bool:
        if not self.arm_client.wait_for_service(timeout_sec=3.0):
            self.publish_state('ARM_SERVICE_TIMEOUT')
            return False
        req = ArmCommand.Request()
        req.command = int(command)
        if target is not None:
            req.class_id = int(target.class_id)
            req.target_pose = target.pose
        fut = self.arm_client.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=timeout_sec)
        return fut.done() and bool(fut.result().accepted)

    def pick_once(self, index: int) -> bool:
        self.publish_state(f'PICK_{index}_START')
        target = self.wait_for_target(self.wait_target_timeout_sec)
        if target is None:
            return False
        self.call_gripper(True)
        ok = self.call_arm(ArmCommand.Request.PICK, target, self.pick_timeout_sec)
        if ok:
            self.call_gripper(False)
        self.publish_state(f'PICK_{index}_{"OK" if ok else "FAIL"}')
        return ok

    def place_once(self, index: int) -> bool:
        self.publish_state(f'PLACE_{index}_START')
        ok = self.call_arm(ArmCommand.Request.PLACE, self.latest_target, self.place_timeout_sec)
        if ok:
            self.call_gripper(True)
        self.publish_state(f'PLACE_{index}_{"OK" if ok else "FAIL"}')
        return ok

    def run_mission(self) -> None:
        mission = self.cfg.get('mission', {})
        visit_zones = list(mission.get('visit_zones', ['B', 'C', 'D']))
        pick_count = int(mission.get('pick_count', 4))
        place_zone = mission.get('place_zone', 'E')
        finish_zone = mission.get('finish_zone', 'F')

        self.publish_state('MISSION_BEGIN')
        for zone in visit_zones:
            if not self.running:
                return
            self.go_to_zone(zone)

        picked = 0
        for i in range(pick_count):
            if not self.running:
                return
            if self.pick_once(i + 1):
                picked += 1

        if self.running:
            self.go_to_zone(place_zone)
        for i in range(picked):
            if not self.running:
                return
            self.place_once(i + 1)

        if self.running:
            self.go_to_zone(finish_zone)
        self.publish_state(f'MISSION_DONE_PICKED_{picked}')
        self.running = False


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MissionNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
