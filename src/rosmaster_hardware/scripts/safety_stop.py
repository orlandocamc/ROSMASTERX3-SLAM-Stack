#!/usr/bin/env python3
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan


class SafetyStop(Node):

    def __init__(self):
        super().__init__('safety_stop')

        self.declare_parameter('safety_distance',    0.3)
        self.declare_parameter('scan_topic',         '/scan')
        self.declare_parameter('input_topic',        '/cmd_vel_in')
        self.declare_parameter('output_topic',       '/cmd_vel_safe')
        self.declare_parameter('enable',             True)
        self.declare_parameter('front_angle_window', 60.0)   # grados

        self._safety_dist = self.get_parameter('safety_distance').value
        self._enable      = self.get_parameter('enable').value
        self._half_window = math.radians(
            self.get_parameter('front_angle_window').value / 2.0
        )
        scan_topic   = self.get_parameter('scan_topic').value
        input_topic  = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value

        self._pub = self.create_publisher(Twist, output_topic, 10)
        self.create_subscription(LaserScan, scan_topic,  self._scan_cb, 10)
        self.create_subscription(Twist,     input_topic, self._cmd_cb,  10)

        self._last_scan:      LaserScan | None = None
        self._last_warn_time: float            = 0.0

        self.get_logger().info(
            f"SafetyStop listo — dist={self._safety_dist}m "
            f"window=±{math.degrees(self._half_window):.0f}° "
            f"enable={self._enable} "
            f"{input_topic} → {output_topic}"
        )

    def _scan_cb(self, msg: LaserScan):
        self._last_scan = msg

    def _cmd_cb(self, msg: Twist):
        if not self._enable or self._last_scan is None:
            self._pub.publish(msg)
            return

        # Reversa y rotación pasan siempre
        if msg.linear.x <= 0.0:
            self._pub.publish(msg)
            return

        min_dist = self._frontal_min_distance(self._last_scan)

        if min_dist < self._safety_dist:
            now = time.monotonic()
            if now - self._last_warn_time >= 1.0:
                self.get_logger().warn(
                    f"Obstáculo a {min_dist:.2f}m — frenado de emergencia"
                )
                self._last_warn_time = now
            self._pub.publish(Twist())
        else:
            self._pub.publish(msg)

    def _frontal_min_distance(self, scan: LaserScan) -> float:
        min_dist = float('inf')
        angle = scan.angle_min
        for r in scan.ranges:
            # Normalizar a [-π, π] para comparar con cono frontal (0 rad = frente)
            a = math.atan2(math.sin(angle), math.cos(angle))
            if abs(a) <= self._half_window and scan.range_min <= r <= scan.range_max:
                if r < min_dist:
                    min_dist = r
            angle += scan.angle_increment
        return min_dist


def main(args=None):
    rclpy.init(args=args)
    node = SafetyStop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
