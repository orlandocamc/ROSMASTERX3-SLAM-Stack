#!/usr/bin/env python3
"""
rosmaster_odom.py

Nodo de odometría para hardware real ROSMASTER X3.
Se suscribe a /vel_raw (geometry_msgs/Twist) publicado por yahboom_driver
para evitar cualquier conflicto de puerto serial.

Tópicos suscritos:
  /vel_raw  geometry_msgs/Twist  — vx, vy, angular_z directos de get_motion_data()

Tópicos publicados:
  /odom  nav_msgs/Odometry  — posición integrada + velocidades + covarianza

Parámetros:
  publish_tf  bool  (default: true) — emitir TF odom→base_footprint.
              Poner false cuando robot_localization EKF gestiona ese TF.

TF publicadas (si publish_tf=true):
  odom → base_footprint
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros


# Covarianza diagonal para ruedas mecanum (row-major, 6×6)
# Las ruedas mecanum tienen deslizamiento lateral → σ_y > σ_x
_POSE_COV = [
    0.01,  0.0,   0.0,   0.0,   0.0,   0.0,
    0.0,   0.02,  0.0,   0.0,   0.0,   0.0,
    0.0,   0.0,   1e6,   0.0,   0.0,   0.0,
    0.0,   0.0,   0.0,   1e6,   0.0,   0.0,
    0.0,   0.0,   0.0,   0.0,   1e6,   0.0,
    0.0,   0.0,   0.0,   0.0,   0.0,   0.04,
]
_TWIST_COV = [
    0.01,  0.0,   0.0,   0.0,   0.0,   0.0,
    0.0,   0.02,  0.0,   0.0,   0.0,   0.0,
    0.0,   0.0,   1e6,   0.0,   0.0,   0.0,
    0.0,   0.0,   0.0,   1e6,   0.0,   0.0,
    0.0,   0.0,   0.0,   0.0,   1e6,   0.0,
    0.0,   0.0,   0.0,   0.0,   0.0,   0.04,
]


class RosmasterOdom(Node):

    def __init__(self):
        super().__init__('rosmaster_odom')

        self.declare_parameter('publish_tf', True)
        self._publish_tf = self.get_parameter('publish_tf').get_parameter_value().bool_value

        # ── Estado integrado ───────────────────────────────────────────────
        self._x = 0.0
        self._y = 0.0
        self._theta = 0.0
        self._last_time = self.get_clock().now()

        # ── Publisher /odom ────────────────────────────────────────────────
        self._odom_pub = self.create_publisher(Odometry, '/odom', 10)

        # ── TF broadcaster ────────────────────────────────────────────────
        self._tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # ── Suscripción a /vel_raw ─────────────────────────────────────────
        self.create_subscription(Twist, '/vel_raw', self._vel_raw_cb, 10)

        self.get_logger().info(
            f'rosmaster_odom iniciado — suscrito a /vel_raw  publish_tf={self._publish_tf}'
        )

    # ── Callback /vel_raw ──────────────────────────────────────────────────

    def _vel_raw_cb(self, msg: Twist):
        vx = msg.linear.x
        vy = msg.linear.y
        vz = msg.angular.z

        now = self.get_clock().now()
        dt = (now - self._last_time).nanoseconds * 1e-9
        self._last_time = now

        # Integración en el marco del robot → marco odom
        self._x     += (vx * math.cos(self._theta) - vy * math.sin(self._theta)) * dt
        self._y     += (vx * math.sin(self._theta) + vy * math.cos(self._theta)) * dt
        self._theta += vz * dt

        # Quaternion desde yaw
        qz = math.sin(self._theta / 2.0)
        qw = math.cos(self._theta / 2.0)

        stamp = now.to_msg()

        # ── Publicar Odometry ──────────────────────────────────────────────
        odom = Odometry()
        odom.header.stamp    = stamp
        odom.header.frame_id = 'odom'
        odom.child_frame_id  = 'base_footprint'

        odom.pose.pose.position.x    = self._x
        odom.pose.pose.position.y    = self._y
        odom.pose.pose.position.z    = 0.0
        odom.pose.pose.orientation.x = 0.0
        odom.pose.pose.orientation.y = 0.0
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw

        odom.twist.twist.linear.x  = vx
        odom.twist.twist.linear.y  = vy
        odom.twist.twist.angular.z = vz

        odom.pose.covariance  = _POSE_COV
        odom.twist.covariance = _TWIST_COV

        self._odom_pub.publish(odom)

        # ── Publicar TF odom → base_footprint (solo si publish_tf=true) ───
        if not self._publish_tf:
            return

        tf_msg = TransformStamped()
        tf_msg.header.stamp    = stamp
        tf_msg.header.frame_id = 'odom'
        tf_msg.child_frame_id  = 'base_footprint'

        tf_msg.transform.translation.x = self._x
        tf_msg.transform.translation.y = self._y
        tf_msg.transform.translation.z = 0.0
        tf_msg.transform.rotation.x    = 0.0
        tf_msg.transform.rotation.y    = 0.0
        tf_msg.transform.rotation.z    = qz
        tf_msg.transform.rotation.w    = qw

        self._tf_broadcaster.sendTransform(tf_msg)


def main(args=None):
    rclpy.init(args=args)
    node = RosmasterOdom()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
