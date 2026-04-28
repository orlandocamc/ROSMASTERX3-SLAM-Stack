#!/usr/bin/env python3
"""Cliente de sensores ZMQ — imprime lidar, odometría y batería en tiempo real.
No requiere ROS2. Instalar: pip install pyzmq
"""
import argparse
import json
import zmq


def fmt_lidar(d: dict) -> str:
    ranges = d.get('ranges', [])
    valid = [r for r in ranges if r > 0]
    mn = min(valid) if valid else float('nan')
    mx = max(valid) if valid else float('nan')
    return (f"LIDAR  | puntos={len(ranges):4d}  "
            f"min={mn:.3f}m  max={mx:.3f}m  "
            f"ts={d.get('ts', 0):.3f}")


def fmt_odom(d: dict) -> str:
    return (f"ODOM   | x={d.get('x', 0):+.3f}  y={d.get('y', 0):+.3f}  "
            f"θ={d.get('theta', 0):+.3f}rad  "
            f"vx={d.get('vx', 0):+.3f}  vy={d.get('vy', 0):+.3f}  "
            f"wz={d.get('wz', 0):+.3f}  ts={d.get('ts', 0):.3f}")


def fmt_stat(d: dict) -> str:
    return f"BATT   | {d.get('v_batt', 0):.3f} V  ts={d.get('ts', 0):.3f}"


def main():
    parser = argparse.ArgumentParser(description='Cliente sensores ZMQ para ROSMASTER X3')
    parser.add_argument('--host', default='localhost', help='IP del robot (default: localhost)')
    parser.add_argument('--port', type=int, default=5001, help='Puerto ZMQ (default: 5001)')
    args = parser.parse_args()

    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(f"tcp://{args.host}:{args.port}")
    sock.setsockopt(zmq.SUBSCRIBE, b'')  # suscribir a todos los topics
    sock.setsockopt(zmq.RCVHWM, 10)

    print(f"[client_sensors] Conectado a tcp://{args.host}:{args.port}")
    print("[client_sensors] Ctrl+C para salir\n")

    try:
        while True:
            parts = sock.recv_multipart()
            if len(parts) < 2:
                continue
            topic = parts[0]
            try:
                data = json.loads(parts[1].decode('utf-8'))
            except Exception:
                continue

            if topic == b'lidar':
                print(fmt_lidar(data))
            elif topic == b'odom':
                print(fmt_odom(data))
            elif topic == b'stat':
                print(fmt_stat(data))
    except KeyboardInterrupt:
        print("\n[client_sensors] Detenido.")
    finally:
        sock.close()
        ctx.term()


if __name__ == '__main__':
    main()
