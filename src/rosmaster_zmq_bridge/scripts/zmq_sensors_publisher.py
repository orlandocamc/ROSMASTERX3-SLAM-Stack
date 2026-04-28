#!/usr/bin/env python3
import math
import json
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from std_msgs.msg import Float32
import zmq


def _quat_to_yaw(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class ZmqSensorsPublisher(Node):

    def __init__(self):
        super().__init__('zmq_sensors_publisher')

        self.declare_parameter('port', 5001)
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('odom_topic', '/odometry/filtered')
        self.declare_parameter('battery_topic', '/battery_voltage')

        port = self.get_parameter('port').value
        scan_topic = self.get_parameter('scan_topic').value
        odom_topic = self.get_parameter('odom_topic').value
        battery_topic = self.get_parameter('battery_topic').value

        self.ctx = zmq.Context()
        self.sock = self.ctx.socket(zmq.PUB)
        self.sock.bind(f"tcp://*:{port}")
        self._lock = threading.Lock()

        self._scan_count = 0
        self._odom_count = 0
        self._batt_count = 0

        qos_sensor = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        qos_reliable = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5
        )

        self.create_subscription(LaserScan, scan_topic, self._scan_cb, qos_sensor)
        self.create_subscription(Odometry, odom_topic, self._odom_cb, qos_sensor)
        self.create_subscription(Float32, battery_topic, self._batt_cb, qos_reliable)

        self.get_logger().info(f"ZMQ sensors publisher listo en puerto {port}")

    def _publish(self, topic_bytes: bytes, payload: dict):
        data = json.dumps(payload).encode('utf-8')
        with self._lock:
            self.sock.send_multipart([topic_bytes, data])

    def _scan_cb(self, msg: LaserScan):
        ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        ranges = [round(float(r), 3) for r in msg.ranges]
        payload = {
            'ts': round(ts, 3),
            'ranges': ranges,
            'angle_min': round(float(msg.angle_min), 3),
            'angle_max': round(float(msg.angle_max), 3),
            'angle_increment': round(float(msg.angle_increment), 6),
            'range_min': round(float(msg.range_min), 3),
            'range_max': round(float(msg.range_max), 3),
        }
        self._publish(b'lidar', payload)
        self._scan_count += 1
        if self._scan_count % 100 == 0:
            self.get_logger().info(f"Lidar publicado: {self._scan_count} veces")

    def _odom_cb(self, msg: Odometry):
        ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        theta = _quat_to_yaw(q)
        t = msg.twist.twist.linear
        w = msg.twist.twist.angular
        payload = {
            'ts': round(ts, 3),
            'x': round(float(p.x), 3),
            'y': round(float(p.y), 3),
            'theta': round(theta, 3),
            'vx': round(float(t.x), 3),
            'vy': round(float(t.y), 3),
            'wz': round(float(w.z), 3),
        }
        self._publish(b'odom', payload)
        self._odom_count += 1
        if self._odom_count % 100 == 0:
            self.get_logger().info(f"Odom publicado: {self._odom_count} veces")

    def _batt_cb(self, msg: Float32):
        ts = time.time()
        payload = {
            'ts': round(ts, 3),
            'v_batt': round(float(msg.data), 3),
        }
        self._publish(b'stat', payload)
        self._batt_count += 1
        if self._batt_count % 100 == 0:
            self.get_logger().info(f"Batería publicada: {self._batt_count} veces")

    def destroy_node(self):
        self.sock.close()
        self.ctx.term()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ZmqSensorsPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
