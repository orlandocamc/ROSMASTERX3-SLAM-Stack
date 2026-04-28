#!/usr/bin/env python3
"""Cliente de video ZMQ — recibe stream RGB (o depth) y lo muestra con OpenCV.
No requiere ROS2. Instalar: pip install pyzmq opencv-python numpy
"""
import argparse
import sys
import numpy as np
import cv2
import zmq


def main():
    parser = argparse.ArgumentParser(description='Cliente video ZMQ para ROSMASTER X3')
    parser.add_argument('--host', default='localhost', help='IP del robot (default: localhost)')
    parser.add_argument('--port', type=int, default=5555, help='Puerto ZMQ (default: 5555)')
    parser.add_argument('--topic', default='rgb', help='Topic: rgb o depth (default: rgb)')
    args = parser.parse_args()

    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(f"tcp://{args.host}:{args.port}")
    sock.setsockopt(zmq.SUBSCRIBE, args.topic.encode())
    sock.setsockopt(zmq.RCVHWM, 2)

    print(f"[client_video] Conectado a tcp://{args.host}:{args.port} | topic={args.topic}")
    print("[client_video] Presiona ESC para salir")

    frame_count = 0
    try:
        while True:
            try:
                parts = sock.recv_multipart(flags=zmq.NOBLOCK)
            except zmq.Again:
                if cv2.waitKey(1) == 27:
                    break
                continue

            if len(parts) < 2:
                continue

            arr = np.frombuffer(parts[1], dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            frame_count += 1
            cv2.imshow(args.topic, frame)
            if cv2.waitKey(1) == 27:
                break
    except KeyboardInterrupt:
        pass
    finally:
        print(f"[client_video] Frames recibidos: {frame_count}")
        cv2.destroyAllWindows()
        sock.close()
        ctx.term()


if __name__ == '__main__':
    main()
