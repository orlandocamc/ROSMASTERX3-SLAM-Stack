# rosmaster_zmq_bridge

Puente bidireccional ROS2 ↔ ZMQ para el robot **ROSMASTER X3** (Yahboom, ruedas mecanum).
Permite que clientes externos (Unity, navegador, Meta Quest 3, scripts Python) reciban datos del robot y le envíen comandos **sin necesitar ROS2 instalado**.

---

## Arquitectura

```
Robot (ROS2 Jazzy)                          Clientes externos
─────────────────                           ─────────────────
/scan          → zmq_sensors_publisher ──▶ PUB:5001  topic b'lidar'
/odometry/filtered                     ──▶ PUB:5001  topic b'odom'
/battery_voltage                       ──▶ PUB:5001  topic b'stat'

/camera/color/image_raw → zmq_video_pub ──▶ PUB:5555  topic b'rgb'
/camera/depth/image_raw [FUTURO]        ──▶ PUB:5556  topic b'depth'

/cmd_vel       ← zmq_cmd_subscriber   ◀── SUB:5002  topic b'cmd'

Flask web UI   ←→ flask_teleop_server  ←── HTTP:5000 (WASD+QE)
```

---

## Tabla de puertos y mensajes

| Puerto | Socket | Topic    | Dirección | Payload                                      |
|--------|--------|----------|-----------|----------------------------------------------|
| 5555   | PUB    | `b'rgb'` | robot→cliente | JPEG bytes de la cámara RGB            |
| 5556   | PUB    | `b'depth'`| robot→cliente | JPEG bytes depth (colormap JET) — FUTURO|
| 5001   | PUB    | `b'lidar'`| robot→cliente | JSON con array `ranges` y metadatos    |
| 5001   | PUB    | `b'odom'` | robot→cliente | JSON con `x, y, theta, vx, vy, wz`    |
| 5001   | PUB    | `b'stat'` | robot→cliente | JSON con `v_batt`                      |
| 5002   | SUB    | `b'cmd'` | cliente→robot | JSON con `vx, vy, wz`                 |
| 5000   | HTTP   | —        | browser→robot | Web UI WASD teleop                     |

### Formato de mensajes ZMQ (multipart)

**Lidar** (`b'lidar'`):
```json
{ "ts": 1234.567, "ranges": [0.5, 0.6, ...], "angle_min": -3.14, "angle_max": 3.14,
  "angle_increment": 0.017, "range_min": 0.15, "range_max": 12.0 }
```

**Odometría** (`b'odom'`):
```json
{ "ts": 1234.567, "x": 0.123, "y": -0.456, "theta": 1.23,
  "vx": 0.1, "vy": 0.0, "wz": 0.05 }
```

**Estado** (`b'stat'`):
```json
{ "ts": 1234.567, "v_batt": 11.8 }
```

**Comando** (`b'cmd'`):
```json
{ "vx": 0.3, "vy": 0.0, "wz": 0.0 }
```

---

## Lanzar el bridge en el robot

```bash
# En el robot (Raspberry Pi 5)
cd ~/ros2_ws_02
source install/setup.bash
ros2 launch rosmaster_zmq_bridge zmq_bridge.launch.py
```

Web UI disponible en: `http://<IP_ROBOT>:5000`

---

## Conectar desde un cliente externo (sin ROS2)

### Instalar dependencias (en la PC del cliente)

```bash
pip install pyzmq opencv-python numpy
pip install pynput   # solo para client_cmd_keyboard.py
```

### Ver video RGB

```bash
python3 client_video.py --host 100.90.163.4 --port 5555 --topic rgb
```

### Ver datos de sensores

```bash
python3 client_sensors.py --host 100.90.163.4
```

### Controlar con teclado

```bash
python3 client_cmd_keyboard.py --host 100.90.163.4
# W/S=adelante/atrás  Q/E=strafe  A/D=rotar  ESPACIO=parar  ESC=salir
```

---

## Para Unity

Usar un plugin ZMQ para Unity (p.ej. `NetMQ` o `AsyncIO.Network.ZMQ`):

| Qué consumir / publicar | Puerto | Topic bytes | Tipo socket |
|------------------------|--------|-------------|-------------|
| Recibir imagen RGB      | 5555   | `rgb`       | SUB         |
| Recibir lidar           | 5001   | `lidar`     | SUB         |
| Recibir odometría       | 5001   | `odom`      | SUB         |
| Enviar comandos         | 5002   | `cmd`       | PUB         |

Todos los mensajes son multipart `[topic_bytes, payload_bytes]`.
El payload JSON usa UTF-8.

---

## Dependencias del sistema

```bash
sudo apt install -y python3-zmq python3-flask
```

---

## Build

```bash
cd ~/ros2_ws_02
colcon build --packages-select rosmaster_zmq_bridge --symlink-install
source install/setup.bash
```
