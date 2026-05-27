from __future__ import annotations

import time
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import Twist
from std_msgs.msg import String
from example_interfaces.srv import SetBool

from smarthome_common_interfaces.msg import CommFrame, LowerState, ObjectTarget
from smarthome_common_interfaces.srv import ArmCommand

from .protocol import (
    CmdId, Frame, FrameParser, CMD_NAMES,
    pack_frame, pack_chassis_vel, pack_object_target, pack_gripper,
    pack_estop, pack_arm_command, unpack_lower_state, unpack_ack,
)
from .serial_transport import SerialTransport


class UnifiedCommNode(Node):
    def __init__(self) -> None:
        super().__init__('smarthome_comm_node')

        self.declare_parameter('serial_device', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('fake_mode', True)
        self.declare_parameter('read_hz', 200.0)
        self.declare_parameter('heartbeat_hz', 2.0)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('object_target_topic', '/smarthome/object_target')
        self.declare_parameter('lower_state_topic', '/smarthome/lower_state')
        self.declare_parameter('raw_rx_topic', '/smarthome/comm/raw_rx')
        self.declare_parameter('raw_tx_topic', '/smarthome/comm/raw_tx')
        self.declare_parameter('enable_cmd_vel', True)
        self.declare_parameter('enable_object_target', True)

        self.seq = 0
        self.rx_count = 0
        self.tx_count = 0
        self.parser = FrameParser()

        fake_mode = bool(self.get_parameter('fake_mode').value)
        device = str(self.get_parameter('serial_device').value)
        baudrate = int(self.get_parameter('baudrate').value)
        self.transport = SerialTransport(device=device, baudrate=baudrate, fake=fake_mode)
        try:
            self.transport.open()
            mode = 'FAKE' if fake_mode else f'{device}@{baudrate}'
            self.get_logger().info(f'unified comm started: {mode}')
        except Exception as exc:
            self.get_logger().error(f'failed to open serial: {exc}')
            raise

        qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
        self.raw_rx_pub = self.create_publisher(CommFrame, str(self.get_parameter('raw_rx_topic').value), qos)
        self.raw_tx_pub = self.create_publisher(CommFrame, str(self.get_parameter('raw_tx_topic').value), qos)
        self.lower_state_pub = self.create_publisher(LowerState, str(self.get_parameter('lower_state_topic').value), qos)
        self.event_pub = self.create_publisher(String, '/smarthome/comm/event', qos)

        if bool(self.get_parameter('enable_cmd_vel').value):
            self.cmd_vel_sub = self.create_subscription(
                Twist,
                str(self.get_parameter('cmd_vel_topic').value),
                self.on_cmd_vel,
                qos,
            )
        if bool(self.get_parameter('enable_object_target').value):
            self.target_sub = self.create_subscription(
                ObjectTarget,
                str(self.get_parameter('object_target_topic').value),
                self.on_object_target,
                qos,
            )

        self.gripper_srv = self.create_service(SetBool, '/smarthome/comm/gripper', self.on_gripper)
        self.estop_srv = self.create_service(SetBool, '/smarthome/comm/set_estop', self.on_estop)
        self.arm_srv = self.create_service(ArmCommand, '/smarthome/comm/arm_command', self.on_arm_command)

        read_period = 1.0 / max(1.0, float(self.get_parameter('read_hz').value))
        heartbeat_period = 1.0 / max(0.1, float(self.get_parameter('heartbeat_hz').value))
        self.read_timer = self.create_timer(read_period, self.read_serial_once)
        self.heartbeat_timer = self.create_timer(heartbeat_period, self.send_heartbeat)
        self.fake_state_timer = self.create_timer(0.5, self.publish_fake_state)

    def destroy_node(self) -> bool:
        self.transport.close()
        return super().destroy_node()

    def _next_seq(self) -> int:
        self.seq = (self.seq + 1) & 0xFF
        return self.seq

    def publish_raw(self, frame: Frame, direction: int) -> None:
        msg = CommFrame()
        msg.stamp = self.get_clock().now().to_msg()
        msg.cmd_id = int(frame.cmd_id)
        msg.seq = int(frame.seq)
        msg.direction = int(direction)
        msg.payload = list(frame.payload)
        msg.crc_ok = bool(frame.crc_ok)
        msg.name = frame.name
        if direction == CommFrame.DIRECTION_RX:
            self.raw_rx_pub.publish(msg)
        else:
            self.raw_tx_pub.publish(msg)

    def send_frame(self, cmd_id: int, payload: bytes = b'') -> None:
        seq = self._next_seq()
        raw = pack_frame(cmd_id, seq, payload)
        self.transport.write(raw)
        self.tx_count += 1
        self.publish_raw(Frame(cmd_id=cmd_id, seq=seq, payload=payload, crc_ok=True), CommFrame.DIRECTION_TX)

    def on_cmd_vel(self, msg: Twist) -> None:
        payload = pack_chassis_vel(msg.linear.x, msg.linear.y, msg.angular.z)
        self.send_frame(CmdId.CHASSIS_VEL, payload)

    def on_object_target(self, msg: ObjectTarget) -> None:
        p = msg.pose.pose.position
        payload = pack_object_target(msg.class_id, msg.source, p.x, p.y, p.z, msg.score)
        self.send_frame(CmdId.VISION_TARGET, payload)

    def on_gripper(self, request: SetBool.Request, response: SetBool.Response) -> SetBool.Response:
        self.send_frame(CmdId.GRIPPER, pack_gripper(request.data))
        response.success = True
        response.message = 'gripper open' if request.data else 'gripper close'
        return response

    def on_estop(self, request: SetBool.Request, response: SetBool.Response) -> SetBool.Response:
        self.send_frame(CmdId.ESTOP, pack_estop(request.data))
        response.success = True
        response.message = 'estop enabled' if request.data else 'estop released'
        return response

    def on_arm_command(self, request: ArmCommand.Request, response: ArmCommand.Response) -> ArmCommand.Response:
        p = request.target_pose.pose.position
        q = request.target_pose.pose.orientation
        payload = pack_arm_command(
            request.command,
            request.class_id,
            (p.x, p.y, p.z),
            (q.x, q.y, q.z, q.w),
        )
        self.send_frame(CmdId.ARM_COMMAND, payload)
        response.accepted = True
        response.message = f'arm command sent: command={request.command}, class_id={request.class_id}'
        return response

    def send_heartbeat(self) -> None:
        # payload: uint32 ROS-time-ms truncated to 32 bits
        now_ms = int(time.time() * 1000) & 0xFFFFFFFF
        self.send_frame(CmdId.HEARTBEAT_TX, now_ms.to_bytes(4, 'little'))

    def read_serial_once(self) -> None:
        data = self.transport.read_available()
        if not data:
            return
        for frame in self.parser.feed(data):
            self.rx_count += 1
            self.publish_raw(frame, CommFrame.DIRECTION_RX)
            if not frame.crc_ok:
                self.get_logger().warn(f'CRC error on {frame.name}')
                continue
            self.handle_frame(frame)

    def handle_frame(self, frame: Frame) -> None:
        if frame.cmd_id == int(CmdId.LOWER_STATE):
            parsed = unpack_lower_state(frame.payload)
            if parsed is None:
                self.get_logger().warn('LOWER_STATE payload too short')
                return
            msg = LowerState()
            msg.stamp = self.get_clock().now().to_msg()
            msg.mode = int(parsed['mode'])
            msg.estop = bool(parsed['estop'])
            msg.battery_voltage = float(parsed['battery_voltage'])
            msg.battery_current = float(parsed['battery_current'])
            msg.chassis_temp = float(parsed['chassis_temp'])
            msg.error_code = int(parsed['error_code'])
            msg.uptime_ms = int(parsed['uptime_ms'])
            msg.rx_count = int(self.rx_count)
            msg.tx_count = int(self.tx_count)
            msg.text = 'real lower state'
            self.lower_state_pub.publish(msg)
        elif frame.cmd_id == int(CmdId.ACK):
            ack = unpack_ack(frame.payload)
            if ack:
                status = 'OK' if ack['ok'] else f'ERR reason={ack["reason"]}'
                self.get_logger().info(f'ACK for 0x{ack["ack_cmd"]:04X}: {status}')
        else:
            ev = String()
            ev.data = f'rx {frame.name} len={len(frame.payload)}'
            self.event_pub.publish(ev)

    def publish_fake_state(self) -> None:
        if not self.transport.fake:
            return
        msg = LowerState()
        msg.stamp = self.get_clock().now().to_msg()
        msg.mode = 1
        msg.estop = False
        msg.battery_voltage = 24.0
        msg.battery_current = 0.5
        msg.chassis_temp = 35.0
        msg.error_code = 0
        msg.uptime_ms = int(time.time() * 1000) & 0xFFFFFFFF
        msg.rx_count = int(self.rx_count)
        msg.tx_count = int(self.tx_count)
        msg.text = 'fake lower state; serial disabled'
        self.lower_state_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = UnifiedCommNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
