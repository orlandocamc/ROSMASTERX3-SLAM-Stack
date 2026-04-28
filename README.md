# 🤖 ROSMASTERX3-SLAM-Stack

> Stack completo de SLAM, teleoperación y streaming para el robot ROSMASTER X3 (Yahboom) sobre ROS2 Jazzy. Incluye fusión IMU+EKF, control PID de heading, bridge ZMQ para clientes remotos sin ROS, interfaz web de teleoperación, y compatibilidad con Foxglove Studio.

> Complete SLAM, teleoperation and streaming stack for the ROSMASTER X3 robot (Yahboom) on ROS2 Jazzy. Includes IMU+EKF fusion, heading PID control, ZMQ bridge for ROS-less remote clients, web teleop interface, and Foxglove Studio compatibility.

---

## 🌐 Languages / Idiomas

**[Documentación en Español](#-español)** | **[Documentation in English](#-english)**

---

## Español

### Características

- **SLAM en tiempo real** con `slam_toolbox` (modo sync) optimizado para casas/oficinas
- **Fusión IMU + odometría** vía `robot_localization` EKF
- **Teleoperación web** desde cualquier navegador (no requiere ROS)
- **Streaming de cámara** vía ZMQ con baja latencia
- **Visualización remota** vía Foxglove Studio
- **Safety stop** automático con LiDAR
- **Heading controller PID** para movimiento más recto
- **Un solo comando** lanza todo el stack

### Arquitectura

```
┌─────────────────────────────────────────┐
│         Raspberry Pi 5 + Ubuntu 24.04   │
│              ROS2 Jazzy                 │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │     rosmaster_hardware          │   │
│  │  - yahboom_driver (STM32)       │   │
│  │  - rosmaster_odom               │   │
│  │  - heading_controller (PID)     │   │
│  │  - safety_stop                  │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │     rosmaster_slam              │   │
│  │  - slam_toolbox (sync)          │   │
│  │  - robot_localization (EKF)     │   │
│  │  - rplidar_ros (A1M8)           │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │     rosmaster_zmq_bridge        │   │
│  │  - Video (puerto 5555)          │   │
│  │  - Sensores (puerto 5001)       │   │
│  │  - Comandos (puerto 5002)       │   │
│  │  - Flask web (puerto 5000)      │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
              ↓
        Tailscale VPN
              ↓
   ┌──────────┴───────────┐
   │                      │
   PC                  Quest 3 / Unity
   - Foxglove          - ROS-TCP-Connector
   - Navegador web     - ZMQ subscribers
```

### Instalación rápida (TL;DR)

```bash
# 1. Clonar el repo en la RPi
git clone https://github.com/orlandocamc/ROSMASTERX3-SLAM-Stack.git
cd ROSMASTERX3-SLAM-Stack

# 2. Ejecutar el script de instalación (cubre TODO)
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh

# 3. Configurar reglas udev (puertos USB fijos)
sudo cp config/99-rosmaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# 4. Copiar paquetes ROS2 y compilar
mkdir -p ~/ros2_ws_02/src
cp -r src/* ~/ros2_ws_02/src/
cd ~/ros2_ws_02
colcon build --symlink-install

# 5. Lanzar todo
source install/setup.bash
ros2 launch rosmaster_bringup full_stack.launch.py
```

**[Guía detallada paso a paso →](SETUP.md)**

### Uso

**Desde la PC (sin ROS instalado):**

| Servicio | URL / Comando | Función |
|----------|---------------|---------|
| Teleop web | `http://IP_DEL_ROBOT:5000` | Mover robot con WASD+QE |
| Foxglove | `wss://IP_DEL_ROBOT:8765` | Ver SLAM y mapa |
| Video | `python3 clients/client_video.py --host IP_DEL_ROBOT` | Stream de cámara |

**Mapear con SLAM:**

1. Lanzar el stack en la RPi
2. Abrir Foxglove → conectar → agregar topics `/scan` y `/map`
3. Mover robot despacio con teleop
4. Cerrar el loop volviendo al punto inicial
5. Guardar el mapa:
   ```bash
   ros2 run nav2_map_server map_saver_cli -f mi_casa
   ```

### Hardware soportado

- **Robot:** ROSMASTER X3 (Yahboom) con ruedas mecanum
- **CPU:** Raspberry Pi 5 (8GB recomendado)
- **LiDAR:** RPLIDAR A1M8 (SLAMTEC)
- **Cámara:** Orbbec Astra Pro Plus (opcional)
- **IMU:** MPU9250 (integrada en STM32 Yahboom)
- **OS:** Ubuntu 24.04 LTS
- **ROS:** ROS2 Jazzy

### Estructura del repo

```
ROSMASTERX3-SLAM-Stack/
├── src/                      # Paquetes ROS2
├── clients/                  # Clientes Python sin ROS
├── config/                   # udev rules, systemd services
├── scripts/                  # Scripts de instalación
├── docs/                     # Documentación e imágenes
├── maps/                     # Mapas generados de ejemplo
├── README.md                 # Este archivo
├── SETUP.md                  # Guía detallada
├── DEPENDENCIES.md           # Lista exhaustiva de dependencias
├── ARCHITECTURE.md           # Diseño del stack
├── TROUBLESHOOTING.md        # Solución de problemas
└── FOR_DANY.md               # Guía de replicación rápida
```

### Dependencias

El script `install_dependencies.sh` cubre **TODO** lo necesario automáticamente:
- ROS2 Jazzy + herramientas de desarrollo
- Paquetes ROS2 (slam_toolbox, robot_localization, rplidar_ros, foxglove_bridge, nav2, etc.)
- Bibliotecas Python (Rosmaster_Lib, pyzmq, flask, aiortc, opencv, numpy<2, etc.)
- Dependencias del sistema (build tools, ffmpeg, libusb, etc.)
- Swap de 4GB para compilación
- Tailscale (opcional)

**Lista completa con explicación de cada paquete:** [DEPENDENCIES.md](DEPENDENCIES.md)

### Problemas comunes

Ver [TROUBLESHOOTING.md](TROUBLESHOOTING.md) para soluciones a errores típicos.

### Para replicar en otro robot

Si recibiste este proyecto y quieres replicarlo en tu propio ROSMASTER X3, lee [FOR_DANY.md](FOR_DANY.md) — es una guía simplificada paso a paso.

### Contribuir

Pull requests bienvenidas. Para cambios grandes, abrir un issue primero.

### Licencia

MIT - Ver [LICENSE](LICENSE)

---

## English

### Features

- **Real-time SLAM** with `slam_toolbox` (sync mode) tuned for indoor environments
- **IMU + odometry fusion** via `robot_localization` EKF
- **Web teleoperation** from any browser (no ROS required)
- **Camera streaming** via ZMQ with low latency
- **Remote visualization** via Foxglove Studio
- **Automatic safety stop** with LiDAR
- **PID heading controller** for straighter motion
- **One-command launch** for the whole stack

### Architecture

Same as Spanish section above — the stack runs entirely on the RPi 5 and exposes its data via standard protocols (HTTP, WebSocket, ZMQ) so any client can connect.

### Quick start

```bash
# 1. Clone on the RPi
git clone https://github.com/orlandocamc/ROSMASTERX3-SLAM-Stack.git
cd ROSMASTERX3-SLAM-Stack

# 2. Run install script (covers EVERYTHING)
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh

# 3. Set up udev rules (fixed USB ports)
sudo cp config/99-rosmaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# 4. Copy ROS2 packages and build
mkdir -p ~/ros2_ws_02/src
cp -r src/* ~/ros2_ws_02/src/
cd ~/ros2_ws_02
colcon build --symlink-install

# 5. Launch everything
source install/setup.bash
ros2 launch rosmaster_bringup full_stack.launch.py
```

**[Detailed step-by-step guide →](SETUP.md)**

### Usage

**From the PC (no ROS needed):**

| Service | URL / Command | Purpose |
|---------|---------------|---------|
| Web teleop | `http://ROBOT_IP:5000` | Drive robot with WASD+QE |
| Foxglove | `wss://ROBOT_IP:8765` | View SLAM and map |
| Video | `python3 clients/client_video.py --host ROBOT_IP` | Camera stream |

**SLAM mapping workflow:**

1. Launch the stack on the RPi
2. Open Foxglove → connect → add `/scan` and `/map` topics
3. Drive the robot slowly with teleop
4. Close the loop by returning to the start point
5. Save the map:
   ```bash
   ros2 run nav2_map_server map_saver_cli -f my_house
   ```

### 🔧 Supported hardware

- **Robot:** ROSMASTER X3 (Yahboom) with mecanum wheels
- **CPU:** Raspberry Pi 5 (8GB recommended)
- **LiDAR:** RPLIDAR A1M8 (SLAMTEC)
- **Camera:** Orbbec Astra Pro Plus (optional)
- **IMU:** MPU9250 (integrated in Yahboom STM32)
- **OS:** Ubuntu 24.04 LTS
- **ROS:** ROS2 Jazzy

### Dependencies

The `install_dependencies.sh` script automatically covers **EVERYTHING**:
- ROS2 Jazzy + development tools
- ROS2 packages (slam_toolbox, robot_localization, rplidar_ros, foxglove_bridge, nav2, etc.)
- Python libraries (Rosmaster_Lib, pyzmq, flask, aiortc, opencv, numpy<2, etc.)
- System dependencies (build tools, ffmpeg, libusb, etc.)
- 4GB swap for compilation
- Tailscale (optional)

**Full list with package explanations:** [DEPENDENCIES.md](DEPENDENCIES.md)

### Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions to common issues.

### Replicating on another robot

If you received this project and want to replicate it on your own ROSMASTER X3, read [FOR_DANY.md](FOR_DANY.md) — it's a simplified step-by-step guide.

### Contributing

Pull requests welcome. For major changes, please open an issue first.

### 📄 License

MIT - See [LICENSE](LICENSE)

---

## Credits / Créditos

Built by Orlando ([@orlandocamc](https://github.com/orlandocamc)) at Universidad Iberoamericana, integrating work from:
- [Yahboom Rosmaster_Lib](https://github.com/YahboomTechnology) — STM32 driver
- [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox) — Steve Macenski
- [robot_localization](https://github.com/cra-ros-pkg/robot_localization) — Tom Moore
- [Antonio Brandi's bumperbot](https://github.com/AntoBrandi) — config patterns
- ZMQ streaming concept from Sebastián's QCAR teleop project