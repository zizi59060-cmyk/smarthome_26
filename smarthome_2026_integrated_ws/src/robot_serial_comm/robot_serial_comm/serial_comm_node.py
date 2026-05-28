from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import String, UInt8

from robot_serial_comm.msg import ObjectTarget

from .protocol import (
    GIMBAL_TO_VISION_SIZE,
    GimbalToVisionParser,
    VISION_TO_GIMBAL_SIZE,
    VisionMode,
    VisionToGimbal,
    bytes_to_hex,
)
from .serial_transport import SerialTransport


@dataclass
class TargetSnapshot:
    class_id: int
    score: float
    x: float
    y: float
    z: float
    stamp_sec: float


class RobotSerialCommNode(Node):
    def __init__(self) -> None:
        super().__init__("robot_serial_comm_node")

        self.declare_parameter("serial_device", "/dev/ttyACM0")
        self.declare_parameter("baudrate", 115200)
        self.declare_parameter("fake_mode", False)
        self.declare_parameter("read_hz", 200.0)
        self.declare_parameter("send_hz", 30.0)
        self.declare_parameter("mode_pub_hz", 10.0)
        self.declare_parameter("target_timeout_sec", 0.5)
        self.declare_parameter("target_topic", "/smarthome/object_target")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("zone_id_topic", "/smarthome/zone_id")
        self.declare_parameter("mode_topic", "/vision_mode")
        self.declare_parameter("raw_tx_topic", "/robot_serial_comm/raw_tx_hex")
        self.declare_parameter("raw_rx_topic", "/robot_serial_comm/raw_rx_hex")
        self.declare_parameter("default_zone_id", 0)
        self.declare_parameter("default_mode", int(VisionMode.IDLE))

        self.latest_target: Optional[TargetSnapshot] = None
        self.latest_twist = Twist()
        self.zone_id = _clamp_u8(self.get_parameter("default_zone_id").value, 0, 6)
        self.current_mode = _clamp_u8(self.get_parameter("default_mode").value, 0, 2)

        self.parser = GimbalToVisionParser()
        self.transport = SerialTransport(
            device=str(self.get_parameter("serial_device").value),
            baudrate=int(self.get_parameter("baudrate").value),
            fake=_as_bool(self.get_parameter("fake_mode").value),
        )
        self.transport.open()

        mode = "FAKE" if self.transport.fake else f"{self.transport.device}@{self.transport.baudrate}"
        self.get_logger().info(f"robot serial comm started: {mode}")
        self.get_logger().info(
            f"VisionToGimbal size={VISION_TO_GIMBAL_SIZE} bytes, "
            f"GimbalToVision size={GIMBAL_TO_VISION_SIZE} bytes"
        )

        self.raw_tx_pub = self.create_publisher(String, str(self.get_parameter("raw_tx_topic").value), 10)
        self.raw_rx_pub = self.create_publisher(String, str(self.get_parameter("raw_rx_topic").value), 10)
        self.mode_pub = self.create_publisher(UInt8, str(self.get_parameter("mode_topic").value), 10)

        self.target_sub = self.create_subscription(
            ObjectTarget,
            str(self.get_parameter("target_topic").value),
            self.on_target,
            10,
        )
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            str(self.get_parameter("cmd_vel_topic").value),
            self.on_cmd_vel,
            10,
        )
        self.zone_sub = self.create_subscription(
            UInt8,
            str(self.get_parameter("zone_id_topic").value),
            self.on_zone_id,
            10,
        )

        read_period = 1.0 / max(1.0, float(self.get_parameter("read_hz").value))
        send_period = 1.0 / max(1.0, float(self.get_parameter("send_hz").value))
        mode_period = 1.0 / max(1.0, float(self.get_parameter("mode_pub_hz").value))
        self.read_timer = self.create_timer(read_period, self.read_serial_once)
        self.send_timer = self.create_timer(send_period, self.send_packet_once)
        self.mode_timer = self.create_timer(mode_period, self.publish_mode_once)

    def destroy_node(self) -> bool:
        self.transport.close()
        return super().destroy_node()

    def now_sec(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def on_target(self, msg: ObjectTarget) -> None:
        pos = msg.pose.pose.position
        stamp = msg.stamp.sec + msg.stamp.nanosec * 1e-9
        if stamp <= 0.0:
            stamp = self.now_sec()
        self.latest_target = TargetSnapshot(
            class_id=int(msg.class_id),
            score=float(msg.score),
            x=float(pos.x),
            y=float(pos.y),
            z=float(pos.z),
            stamp_sec=stamp,
        )

    def on_cmd_vel(self, msg: Twist) -> None:
        self.latest_twist = msg

    def on_zone_id(self, msg: UInt8) -> None:
        self.zone_id = _clamp_u8(msg.data, 0, 6)

    def build_packet(self) -> VisionToGimbal:
        target = self.latest_target
        target_fresh = False
        if target is not None:
            target_fresh = self.now_sec() - target.stamp_sec <= float(
                self.get_parameter("target_timeout_sec").value
            )

        has_target = bool(target_fresh and target is not None and target.class_id >= 0)
        twist = self.latest_twist
        return VisionToGimbal(
            command=1 if has_target else 0,
            class_id=target.class_id if has_target and target is not None else -1,
            zone_id=self.zone_id,
            x=target.x if has_target and target is not None else 0.0,
            y=target.y if has_target and target is not None else 0.0,
            z=target.z if has_target and target is not None else 0.0,
            vx=float(twist.linear.x),
            vy=float(twist.linear.y),
            wz=float(twist.angular.z),
        )

    def send_packet_once(self) -> None:
        packet = self.build_packet()
        raw = packet.pack()
        try:
            self.transport.write(raw)
        except Exception as exc:
            self.get_logger().error(f"serial write failed: {exc}")
            return

        msg = String()
        msg.data = bytes_to_hex(raw)
        self.raw_tx_pub.publish(msg)

    def read_serial_once(self) -> None:
        try:
            data = self.transport.read_available()
        except Exception as exc:
            self.get_logger().error(f"serial read failed: {exc}")
            return
        if not data:
            return

        rx = String()
        rx.data = bytes_to_hex(data)
        self.raw_rx_pub.publish(rx)

        for frame in self.parser.feed(data):
            if not frame.crc_ok:
                self.get_logger().warn("GimbalToVision CRC mismatch")
                continue
            if frame.mode not in (int(VisionMode.IDLE), int(VisionMode.DETECT_OBJECT), int(VisionMode.DETECT_QR)):
                self.get_logger().warn(f"unknown vision mode from lower computer: {frame.mode}")
                continue
            if frame.mode != self.current_mode:
                self.get_logger().info(f"vision mode changed: {self.current_mode} -> {frame.mode}")
            self.current_mode = int(frame.mode)
            self.publish_mode_once()

    def publish_mode_once(self) -> None:
        msg = UInt8()
        msg.data = int(self.current_mode)
        self.mode_pub.publish(msg)


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _clamp_u8(value, min_value: int = 0, max_value: int = 255) -> int:
    try:
        raw = int(value)
    except (TypeError, ValueError):
        raw = min_value
    return max(min_value, min(max_value, raw))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RobotSerialCommNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
