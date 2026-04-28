#!/usr/bin/env python3
import threading
import rclpy
from rclpy.node import Node
import zmq
import cv2
import numpy as np


class FrameGrabber:
    """Hilo dedicado V4L2 que mantiene siempre el último JPEG disponible."""

    def __init__(self, device, width, height, fps, quality):
        self._device  = device
        self._width   = width
        self._height  = height
        self._fps     = fps
        self._quality = quality
        self._jpeg    = None
        self._lock    = threading.Lock()
        self._running = False
        self._frame_count = 0
        self._cap     = None

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False

    def latest_jpeg(self):
        with self._lock:
            return self._jpeg

    def _loop(self):
        cap = cv2.VideoCapture(self._device, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self._width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        cap.set(cv2.CAP_PROP_FPS,          self._fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)
        self._cap = cap

        actual_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        fourcc     = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
        print(f"[zmq_video] /dev/video{self._device} "
              f"{actual_w}x{actual_h}@{actual_fps:.0f}fps fourcc={fourcc_str}", flush=True)

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self._quality]
        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue
            ok, buf = cv2.imencode('.jpg', frame, encode_params)
            if ok:
                with self._lock:
                    self._jpeg = buf.tobytes()
            self._frame_count += 1
            if self._frame_count % 150 == 0:
                print(f"[zmq_video] Frames RGB enviados: {self._frame_count}", flush=True)
        cap.release()


class ZmqVideoPublisher(Node):

    def __init__(self):
        super().__init__('zmq_video_publisher')

        self.declare_parameter('video_device', 1)
        self.declare_parameter('video_width',  320)
        self.declare_parameter('video_height', 240)
        self.declare_parameter('video_fps',    30)
        self.declare_parameter('rgb_port',     5555)
        self.declare_parameter('depth_port',   5556)
        self.declare_parameter('jpeg_quality', 40)
        self.declare_parameter('enable_depth', False)

        device       = self.get_parameter('video_device').value
        width        = self.get_parameter('video_width').value
        height       = self.get_parameter('video_height').value
        fps          = self.get_parameter('video_fps').value
        rgb_port     = self.get_parameter('rgb_port').value
        depth_port   = self.get_parameter('depth_port').value
        quality      = self.get_parameter('jpeg_quality').value
        self.enable_depth = self.get_parameter('enable_depth').value

        self.ctx = zmq.Context()

        self.rgb_sock = self.ctx.socket(zmq.PUB)
        self.rgb_sock.setsockopt(zmq.SNDHWM, 2)
        self.rgb_sock.bind(f"tcp://*:{rgb_port}")

        # Socket depth: preparado pero suscripción desactivada hasta que la cámara esté disponible
        self.depth_sock = self.ctx.socket(zmq.PUB)
        self.depth_sock.setsockopt(zmq.SNDHWM, 2)
        self.depth_sock.bind(f"tcp://*:{depth_port}")

        self._grabber = FrameGrabber(
            device=device, width=width, height=height, fps=fps, quality=quality
        )
        self._grabber.start()

        # Timer que publica el último JPEG disponible a la frecuencia del sensor
        self._pub_timer = self.create_timer(1.0 / max(fps, 1), self._publish_frame)

        self.get_logger().info(
            f"ZMQ video publisher listo — /dev/video{device} {width}x{height}@{fps}fps "
            f"RGB:{rgb_port}, Depth:{depth_port}, depth_enable={self.enable_depth}"
        )

    def _publish_frame(self):
        jpeg = self._grabber.latest_jpeg()
        if jpeg is None:
            return
        self.rgb_sock.send_multipart([b'rgb', jpeg])

    # Código depth preparado para cuando la cámara esté disponible.
    # Para activar: pasar enable_depth:=true y conectar el callback a un topic ROS2 o
    # a un segundo FrameGrabber apuntando al dispositivo depth.
    def _depth_callback_example(self, depth_np: np.ndarray):
        valid = depth_np[depth_np > 0]
        if valid.size == 0:
            return
        d_min, d_max = valid.min(), valid.max()
        if d_max == d_min:
            return
        normalized = np.clip((depth_np - d_min) / (d_max - d_min), 0.0, 1.0)
        colored = cv2.applyColorMap((normalized * 255).astype(np.uint8), cv2.COLORMAP_JET)
        ok, buf = cv2.imencode('.jpg', colored, [cv2.IMWRITE_JPEG_QUALITY, 40])
        if ok:
            self.depth_sock.send_multipart([b'depth', buf.tobytes()])

    def destroy_node(self):
        self._grabber.stop()
        self.rgb_sock.close()
        self.depth_sock.close()
        self.ctx.term()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ZmqVideoPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
