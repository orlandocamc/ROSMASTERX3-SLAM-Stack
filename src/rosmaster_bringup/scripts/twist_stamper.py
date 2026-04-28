#!/usr/bin/env python3
"""
twist_stamper.py

Convierte geometry_msgs/Twist publicado en /cmd_vel a
geometry_msgs/TwistStamped y lo publica en
/mecanum_drive_controller/reference.

El mecanum_drive_controller de ROS2 Jazzy requiere TwistStamped
en su topic 'reference' en lugar del Twist estándar de /cmd_vel.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped


class TwistStamper(Node):

    def __init__(self):
        super().__init__('twist_stamper')
        self._pub = self.create_publisher(
            TwistStamped,
            '/mecanum_drive_controller/reference',
            10,
        )
        self._sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self._cb,
            10,
        )

    def _cb(self, msg: Twist):
        out = TwistStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'base_footprint'
        out.twist = msg
        self._pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = TwistStamper()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
