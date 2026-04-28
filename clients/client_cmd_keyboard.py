#!/usr/bin/env python3
"""Cliente de teclado ZMQ — envía comandos al robot desde cualquier PC sin ROS2.
Instalar: pip install pyzmq pynput
Teclas: W/S=adelante/atrás, Q/E=strafe izq/der, A/D=rotar izq/der, Espacio=parar, ESC=salir
"""
import argparse
import json
import threading
import time
import zmq

try:
    from pynput import keyboard as pynput_kb
    USE_PYNPUT = True
except ImportError:
    USE_PYNPUT = False

LINEAR_STEP = 0.3
ANGULAR_STEP = 1.0

BINDINGS = {
    'w': ('vx', +1),
    's': ('vx', -1),
    'q': ('vy', +1),
    'e': ('vy', -1),
    'a': ('wz', +1),
    'd': ('wz', -1),
}

pressed = set()
running = True


def compute_cmd(linear: float, angular: float) -> dict:
    vx, vy, wz = 0.0, 0.0, 0.0
    for k, (axis, sign) in BINDINGS.items():
        if k in pressed:
            if axis == 'vx':
                vx += sign * linear
            elif axis == 'vy':
                vy += sign * linear
            elif axis == 'wz':
                wz += sign * angular
    return {'vx': vx, 'vy': vy, 'wz': wz}


def send_loop(sock, linear: float, angular: float):
    global running
    while running:
        cmd = compute_cmd(linear, angular)
        sock.send_multipart([b'cmd', json.dumps(cmd).encode()])
        time.sleep(0.1)


def run_pynput(sock, linear: float, angular: float):
    global running

    def on_press(key):
        try:
            k = key.char.lower() if hasattr(key, 'char') and key.char else None
        except Exception:
            k = None
        if k in BINDINGS:
            pressed.add(k)
        if key == pynput_kb.Key.space:
            pressed.clear()
        if key == pynput_kb.Key.esc:
            running = False
            return False

    def on_release(key):
        try:
            k = key.char.lower() if hasattr(key, 'char') and key.char else None
        except Exception:
            k = None
        if k in BINDINGS:
            pressed.discard(k)

    t = threading.Thread(target=send_loop, args=(sock, linear, angular), daemon=True)
    t.start()

    with pynput_kb.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    running = False
    t.join(timeout=1.0)


def run_curses(sock, linear: float, angular: float):
    import curses

    def _main(stdscr):
        global running
        curses.cbreak()
        stdscr.nodelay(True)
        stdscr.clear()
        stdscr.addstr(0, 0, "ROSMASTER X3 — Teclado ZMQ")
        stdscr.addstr(2, 0, "W/S: adelante/atrás  Q/E: strafe  A/D: rotar")
        stdscr.addstr(3, 0, "ESPACIO: parar  ESC/q: salir")

        t = threading.Thread(target=send_loop, args=(sock, linear, angular), daemon=True)
        t.start()

        while running:
            try:
                ch = stdscr.getch()
            except Exception:
                ch = -1
            if ch == -1:
                time.sleep(0.02)
                continue
            c = chr(ch).lower()
            if c == '\x1b' or c == 'q':
                running = False
                break
            if c == ' ':
                pressed.clear()
            elif c in BINDINGS:
                pressed.add(c)
            stdscr.addstr(5, 0, f"pressed: {sorted(pressed)}    ")
            stdscr.refresh()

        running = False
        t.join(timeout=1.0)

    curses.wrapper(_main)


def main():
    parser = argparse.ArgumentParser(description='Cliente teclado ZMQ para ROSMASTER X3')
    parser.add_argument('--host', default='localhost', help='IP del robot')
    parser.add_argument('--port', type=int, default=5002, help='Puerto ZMQ cmd (default: 5002)')
    parser.add_argument('--linear', type=float, default=LINEAR_STEP, help='Velocidad lineal m/s')
    parser.add_argument('--angular', type=float, default=ANGULAR_STEP, help='Velocidad angular rad/s')
    args = parser.parse_args()

    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUB)
    sock.connect(f"tcp://{args.host}:{args.port}")

    print(f"[client_cmd_keyboard] Conectado a tcp://{args.host}:{args.port}")
    print("Controles: W/S=adelante/atrás  Q/E=strafe  A/D=rotar  ESPACIO=parar  ESC=salir")
    print(f"Velocidades: linear={args.linear} m/s  angular={args.angular} rad/s\n")

    try:
        if USE_PYNPUT:
            run_pynput(sock, args.linear, args.angular)
        else:
            print("[AVISO] pynput no instalado — usando modo curses (menos responsivo)")
            run_curses(sock, args.linear, args.angular)
    except KeyboardInterrupt:
        pass
    finally:
        # Enviar stop antes de cerrar
        sock.send_multipart([b'cmd', json.dumps({'vx': 0.0, 'vy': 0.0, 'wz': 0.0}).encode()])
        time.sleep(0.15)
        sock.close()
        ctx.term()
        print("[client_cmd_keyboard] Detenido.")


if __name__ == '__main__':
    main()
