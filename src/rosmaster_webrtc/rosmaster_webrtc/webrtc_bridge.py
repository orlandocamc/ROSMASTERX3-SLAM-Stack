"""
ROSMASTER X3 — MJPEG HTTP bridge
Captura V4L2 directamente y sirve multipart/x-mixed-replace.
Latencia ~50-100ms, sin encoding H264/VP8 en CPU.
"""
import asyncio
import threading
import logging

from ament_index_python.packages import get_package_share_directory

import rclpy
from rclpy.node import Node

import cv2
import numpy as np
import pathlib
from aiohttp import web

logging.basicConfig(level=logging.INFO)


class FrameGrabber:
    """Hilo dedicado que mantiene siempre el último JPEG disponible."""

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

        actual_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        fourcc     = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
        print(f"[mjpeg_bridge] /dev/video{self._device} "
              f"{actual_w}x{actual_h}@{actual_fps:.0f}fps fourcc={fourcc_str}", flush=True)

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self._quality]
        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue
            ok, jpeg = cv2.imencode('.jpg', frame, encode_params)
            if ok:
                with self._lock:
                    self._jpeg = jpeg.tobytes()
            self._frame_count += 1
            if self._frame_count % 300 == 0:
                print(f"[mjpeg_bridge] frames: {self._frame_count}", flush=True)
        cap.release()


class MJPEGBridgeNode(Node):
    def __init__(self):
        super().__init__("mjpeg_bridge")
        self.declare_parameter("video_device",  0)
        self.declare_parameter("video_width",   640)
        self.declare_parameter("video_height",  480)
        self.declare_parameter("video_fps",     30)
        self.declare_parameter("jpeg_quality",  75)
        self.declare_parameter("http_host",     "0.0.0.0")
        self.declare_parameter("http_port",     8080)

        self.video_device  = self.get_parameter("video_device").value
        self.video_width   = self.get_parameter("video_width").value
        self.video_height  = self.get_parameter("video_height").value
        self.video_fps     = self.get_parameter("video_fps").value
        self.jpeg_quality  = self.get_parameter("jpeg_quality").value
        self.http_host     = self.get_parameter("http_host").value
        self.http_port     = self.get_parameter("http_port").value

        self.get_logger().info(
            f"MJPEG bridge\n"
            f"  device : /dev/video{self.video_device} "
            f"{self.video_width}x{self.video_height}@{self.video_fps}fps\n"
            f"  quality: {self.jpeg_quality}\n"
            f"  http   : {self.http_host}:{self.http_port}"
        )


def build_app(node, grabber):
    web_dir = pathlib.Path(get_package_share_directory('rosmaster_webrtc')) / 'web'
    interval = 1.0 / max(node.video_fps, 1)

    async def index(request):
        f = web_dir / "index.html"
        return web.FileResponse(f) if f.exists() else web.Response(
            text="index.html not found", status=404)

    async def mjpeg_stream(request):
        response = web.StreamResponse(headers={
            'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        })
        await response.prepare(request)
        while True:
            jpeg = grabber.latest_jpeg()
            if jpeg:
                try:
                    await response.write(
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' +
                        jpeg + b'\r\n'
                    )
                except Exception:
                    break
            await asyncio.sleep(interval)
        return response

    app = web.Application()
    app.router.add_get('/',       index)
    app.router.add_get('/stream', mjpeg_stream)
    return app


def main():
    rclpy.init()
    node = MJPEGBridgeNode()

    grabber = FrameGrabber(
        device=node.video_device,
        width=node.video_width,
        height=node.video_height,
        fps=node.video_fps,
        quality=node.jpeg_quality,
    )
    grabber.start()

    stop_event = threading.Event()

    def ros_spin():
        while not stop_event.is_set():
            rclpy.spin_once(node, timeout_sec=0.05)

    spin_thread = threading.Thread(target=ros_spin, daemon=True)
    spin_thread.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        app = build_app(node, grabber)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, node.http_host, node.http_port)
        await site.start()
        node.get_logger().info(
            f"Stream MJPEG en http://0.0.0.0:{node.http_port}/stream"
        )
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()

    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        pass
    finally:
        grabber.stop()
        stop_event.set()
        spin_thread.join(timeout=2)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
