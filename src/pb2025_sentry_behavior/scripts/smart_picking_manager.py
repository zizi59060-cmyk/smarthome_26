#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node

from example_interfaces.srv import Trigger
from std_msgs.msg import String, UInt8

from robot_serial_comm.msg import ObjectTarget


ZONE_IDS = {
    "NONE": 0,
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
}


@dataclass
class TargetState:
    class_id: int = -1
    score: float = 0.0


class SmartPickingManager(Node):
    def __init__(self) -> None:
        super().__init__("smart_picking_manager")

        self.declare_parameter("auto_start", True)
        self.declare_parameter("target_topic", "/smarthome/object_target")
        self.declare_parameter("vision_mode_topic", "/vision_mode")
        self.declare_parameter("zone_id_topic", "/smarthome/zone_id")
        self.declare_parameter("zone_name_topic", "/smarthome/zone_name")
        self.declare_parameter("state_topic", "/smarthome/smart_picking/state")
        self.declare_parameter("initial_zone", "NONE")
        self.declare_parameter("publish_hz", 10.0)

        self.running = _as_bool(self.get_parameter("auto_start").value)
        self.zone_name = _normalize_zone(str(self.get_parameter("initial_zone").value))
        self.vision_mode = 0
        self.latest_target = TargetState()
        self.last_state = ""

        self.zone_pub = self.create_publisher(UInt8, str(self.get_parameter("zone_id_topic").value), 10)
        self.state_pub = self.create_publisher(String, str(self.get_parameter("state_topic").value), 10)

        self.target_sub = self.create_subscription(
            ObjectTarget,
            str(self.get_parameter("target_topic").value),
            self.on_target,
            10,
        )
        self.mode_sub = self.create_subscription(
            UInt8,
            str(self.get_parameter("vision_mode_topic").value),
            self.on_mode,
            10,
        )
        self.zone_name_sub = self.create_subscription(
            String,
            str(self.get_parameter("zone_name_topic").value),
            self.on_zone_name,
            10,
        )

        self.start_srv = self.create_service(Trigger, "/smarthome/smart_picking/start", self.on_start)
        self.stop_srv = self.create_service(Trigger, "/smarthome/smart_picking/stop", self.on_stop)

        period = 1.0 / max(1.0, float(self.get_parameter("publish_hz").value))
        self.timer = self.create_timer(period, self.on_timer)
        self.publish_state(force=True)

    def on_target(self, msg: ObjectTarget) -> None:
        self.latest_target = TargetState(class_id=int(msg.class_id), score=float(msg.score))
        self.publish_state()

    def on_mode(self, msg: UInt8) -> None:
        self.vision_mode = int(msg.data)
        self.publish_state()

    def on_zone_name(self, msg: String) -> None:
        self.zone_name = _normalize_zone(msg.data)
        self.publish_state(force=True)

    def on_start(self, request, response):
        self.running = True
        self.publish_state(force=True)
        response.success = True
        response.message = "smart picking started"
        return response

    def on_stop(self, request, response):
        self.running = False
        self.publish_state(force=True)
        response.success = True
        response.message = "smart picking stopped"
        return response

    def on_timer(self) -> None:
        msg = UInt8()
        msg.data = ZONE_IDS[self.zone_name] if self.running else 0
        self.zone_pub.publish(msg)

    def publish_state(self, force: bool = False) -> None:
        state = (
            f"running={int(self.running)} "
            f"zone={self.zone_name} "
            f"mode={self.vision_mode} "
            f"class_id={self.latest_target.class_id} "
            f"score={self.latest_target.score:.3f}"
        )
        if force or state != self.last_state:
            msg = String()
            msg.data = state
            self.state_pub.publish(msg)
            self.last_state = state


def _normalize_zone(value: str) -> str:
    zone = value.strip().upper()
    return zone if zone in ZONE_IDS else "NONE"


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SmartPickingManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
