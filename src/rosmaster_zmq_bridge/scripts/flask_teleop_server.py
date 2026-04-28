#!/usr/bin/env python3
import argparse
import json
import logging
import zmq
from flask import Flask, request, jsonify

HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ROSMASTER X3 Teleop</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d0d0d;
    color: #e0e0e0;
    font-family: 'Courier New', monospace;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    gap: 24px;
    user-select: none;
  }
  h1 { font-size: 1.4rem; letter-spacing: 4px; color: #00e5ff; text-transform: uppercase; }
  .status {
    font-size: 1rem;
    color: #80ff80;
    letter-spacing: 2px;
    background: #1a1a1a;
    padding: 8px 20px;
    border-radius: 4px;
    border: 1px solid #333;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(3, 72px);
    grid-template-rows: repeat(2, 72px);
    gap: 8px;
  }
  .key {
    background: #1e1e1e;
    border: 2px solid #444;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
    font-weight: bold;
    color: #bbb;
    cursor: pointer;
    transition: background 0.1s, border-color 0.1s, color 0.1s;
    -webkit-tap-highlight-color: transparent;
  }
  .key .hint { font-size: 0.55rem; color: #666; margin-top: 3px; letter-spacing: 1px; }
  .key.active { background: #003d52; border-color: #00e5ff; color: #00e5ff; }
  .legend {
    font-size: 0.75rem;
    color: #555;
    text-align: center;
    line-height: 1.7;
  }
</style>
</head>
<body>
<h1>ROSMASTER X3</h1>
<div class="status" id="vel">vx: 0.000 | vy: 0.000 | wz: 0.000</div>
<div class="grid">
  <div class="key" id="key-q" data-key="q">Q<span class="hint">STR-IZQ</span></div>
  <div class="key" id="key-w" data-key="w">W<span class="hint">ADELANTE</span></div>
  <div class="key" id="key-e" data-key="e">E<span class="hint">STR-DER</span></div>
  <div class="key" id="key-a" data-key="a">A<span class="hint">ROT-IZQ</span></div>
  <div class="key" id="key-s" data-key="s">S<span class="hint">ATRÁS</span></div>
  <div class="key" id="key-d" data-key="d">D<span class="hint">ROT-DER</span></div>
</div>
<div class="legend">
  W/S — avance · Q/E — strafe lateral · A/D — rotación<br>
  Mantén pulsado para mover · Suelta para parar
</div>
<script>
const pressed = new Set();
const LINEAR = __LINEAR__;
const ANGULAR = __ANGULAR__;

function computeVels() {
  let vx = 0, vy = 0, wz = 0;
  if (pressed.has('w')) vx += LINEAR;
  if (pressed.has('s')) vx -= LINEAR;
  if (pressed.has('q')) vy += LINEAR;
  if (pressed.has('e')) vy -= LINEAR;
  if (pressed.has('a')) wz += ANGULAR;
  if (pressed.has('d')) wz -= ANGULAR;
  return { vx, vy, wz };
}

function sendCmd() {
  const v = computeVels();
  document.getElementById('vel').textContent =
    `vx: ${v.vx.toFixed(3)} | vy: ${v.vy.toFixed(3)} | wz: ${v.wz.toFixed(3)}`;
  fetch('/control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(v)
  }).catch(() => {});
}

document.addEventListener('keydown', e => {
  const k = e.key.toLowerCase();
  if ('wsqead'.includes(k) && k.length === 1) {
    e.preventDefault();
    pressed.add(k);
    document.getElementById('key-' + k)?.classList.add('active');
  }
});
document.addEventListener('keyup', e => {
  const k = e.key.toLowerCase();
  pressed.delete(k);
  document.getElementById('key-' + k)?.classList.remove('active');
});

document.querySelectorAll('.key').forEach(el => {
  const k = el.dataset.key;
  el.addEventListener('touchstart', ev => { ev.preventDefault(); pressed.add(k); el.classList.add('active'); }, { passive: false });
  el.addEventListener('touchend',   ev => { ev.preventDefault(); pressed.delete(k); el.classList.remove('active'); }, { passive: false });
  el.addEventListener('mousedown',  () => { pressed.add(k); el.classList.add('active'); });
  el.addEventListener('mouseup',    () => { pressed.delete(k); el.classList.remove('active'); });
  el.addEventListener('mouseleave', () => { pressed.delete(k); el.classList.remove('active'); });
});

setInterval(sendCmd, 100);
</script>
</body>
</html>
"""


def build_app(linear_speed: float, angular_speed: float, zmq_sock) -> Flask:
    app = Flask(__name__)
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    html = (
        HTML_PAGE
        .replace('__LINEAR__', str(linear_speed))
        .replace('__ANGULAR__', str(angular_speed))
    )

    @app.route('/')
    def index():
        return html

    @app.route('/control', methods=['POST'])
    def control():
        data = request.get_json(silent=True) or {}
        vx = float(data.get('vx', 0.0))
        vy = float(data.get('vy', 0.0))
        wz = float(data.get('wz', 0.0))
        payload = json.dumps({'vx': vx, 'vy': vy, 'wz': wz}).encode()
        zmq_sock.send_multipart([b'cmd', payload])
        return jsonify(ok=True)

    return app


def main():
    parser = argparse.ArgumentParser(description='Flask teleop web UI para ROSMASTER X3')
    parser.add_argument('--port-web', type=int, default=5000)
    parser.add_argument('--cmd-zmq-port', type=int, default=5002)
    parser.add_argument('--host-zmq', default='localhost')
    parser.add_argument('--linear-speed', type=float, default=0.15)
    parser.add_argument('--angular-speed', type=float, default=0.6)
    args = parser.parse_args()

    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUB)
    sock.connect(f"tcp://{args.host_zmq}:{args.cmd_zmq_port}")

    print(f"[flask_teleop] Conectado a ZMQ tcp://{args.host_zmq}:{args.cmd_zmq_port}")
    print(f"[flask_teleop] Web UI en http://0.0.0.0:{args.port_web}")

    app = build_app(args.linear_speed, args.angular_speed, sock)
    try:
        app.run(host='0.0.0.0', port=args.port_web, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        ctx.term()


if __name__ == '__main__':
    main()
