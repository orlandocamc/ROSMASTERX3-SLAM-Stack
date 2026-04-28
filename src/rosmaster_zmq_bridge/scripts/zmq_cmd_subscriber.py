#!/usr/bin/env python3
import json
import threading
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import zmq


class ZmqCmdSubscriber(Node):

    def __init__(self):
        super().__init__('zmq_cmd_subscriber')

        self.declare_parameter('port', 5002)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel_in')
        self.declare_parameter('watchdog_timeout', 0.5)
        self.declare_parameter('max_linear', 0.2)
        self.declare_parameter('max_angular', 0.6)

        port = self.get_parameter('port').value
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.watchdog_timeout = self.get_parameter('watchdog_timeout').value
        self.max_linear = self.get_parameter('max_linear').value
        self.max_angular = self.get_parameter('max_angular').value

        self.pub = self.create_publisher(Twist, cmd_vel_topic, 10)

        self.ctx = zmq.Context()
        self.sock = self.ctx.socket(zmq.SUB)
        self.sock.bind(f"tcp://*:{port}")
        self.sock.setsockopt(zmq.SUBSCRIBE, b'')
        self.sock.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout para el poll

        self._last_cmd_time = time.time()
        self._cmd_count = 0
        self._running = True

        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

        self.create_timer(0.1, self._watchdog_cb)

        self.get_logger().info(
            f"ZMQ cmd subscriber listo en puerto {port}, "
            f"watchdog={self.watchdog_timeout}s, "
            f"max_linear={self.max_linear}, max_angular={self.max_angular}"
        )

    def _recv_loop(self):
        while self._running:
            try:
                parts = self.sock.recv_multipart()
            except zmq.Again:
                continue
            except zmq.ZMQError:
                break

            if len(parts) < 2:
                continue
            topic, payload = parts[0], parts[1]
            if topic != b'cmd':
                continue

            try:
                data = json.loads(payload.decode('utf-8'))
            except Exception:
                continue

            vx = float(data.get('vx', 0.0))
            vy = float(data.get('vy', 0.0))
            wz = float(data.get('wz', 0.0))

            vx = max(-self.max_linear, min(self.max_linear, vx))
            vy = max(-self.max_linear, min(self.max_linear, vy))
            wz = max(-self.max_angular, min(self.max_angular, wz))

            twist = Twist()
            twist.linear.x = vx
            twist.linear.y = vy
            twist.angular.z = wz
            self.pub.publish(twist)

            self._last_cmd_time = time.time()
            self._cmd_count += 1
            if self._cmd_count % 10 == 0:
                self.get_logger().info(
                    f"Comando recibido vx={vx:.2f} vy={vy:.2f} wz={wz:.2f}"
                )

    def _watchdog_cb(self):
        if time.time() - self._last_cmd_time > self.watchdog_timeout:
            twist = Twist()
            self.pub.publish(twist)

    def destroy_node(self):
        self._running = False
        self._recv_thread.join(timeout=1.0)
        self.sock.close()
        self.ctx.term()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ZmqCmdSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
