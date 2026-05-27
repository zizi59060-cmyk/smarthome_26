from __future__ import annotations

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from smarthome_common_interfaces.msg import ObjectTarget


class VisionPoseAdapter(Node):
    """Generic adapter from PoseStamped to ObjectTarget.

    Use this node when a vision module can output only a PoseStamped.
    For the real smarthome_vision package, the preferred integration is to publish
    ObjectTarget directly from vision_node and keep all serial I/O in smarthome_comm.
    """

    def __init__(self) -> None:
        super().__init__('vision_pose_adapter')
        self.declare_parameter('input_pose_topic', '/vision/target_pose')
        self.declare_parameter('output_target_topic', '/smarthome/object_target')
        self.declare_parameter('class_id', 0)
        self.declare_parameter('score', 1.0)
        self.declare_parameter('source', int(ObjectTarget.SOURCE_OBJECT))
        self.declare_parameter('label', 'adapter_target')
        self.pub = self.create_publisher(ObjectTarget, str(self.get_parameter('output_target_topic').value), 10)
        self.sub = self.create_subscription(PoseStamped, str(self.get_parameter('input_pose_topic').value), self.on_pose, 10)

    def on_pose(self, msg: PoseStamped) -> None:
        out = ObjectTarget()
        out.stamp = self.get_clock().now().to_msg()
        out.class_id = int(self.get_parameter('class_id').value)
        out.pose = msg
        out.score = float(self.get_parameter('score').value)
        out.source = int(self.get_parameter('source').value)
        out.label = str(self.get_parameter('label').value)
        self.pub.publish(out)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VisionPoseAdapter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
