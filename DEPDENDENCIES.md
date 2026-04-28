# 📦 DEPENDENCIES — Todas las dependencias / All dependencies

> Lista exhaustiva de todo lo que el script `install_dependencies.sh` instala, organizado por categoría y con su propósito.

> Comprehensive list of everything installed by `install_dependencies.sh`, organized by category with its purpose.

---

## 🇪🇸 Español

### 🤖 ROS2 Jazzy (paquete base)

| Paquete | Para qué sirve |
|---------|----------------|
| `ros-jazzy-desktop` | Instalación completa de ROS2 con RViz2 |
| `ros-dev-tools` | Herramientas de desarrollo (build, debug) |
| `python3-colcon-common-extensions` | Build system para paquetes ROS2 |
| `python3-rosdep` | Resolver dependencias de paquetes ROS2 |
| `python3-vcstool` | Manejo de múltiples repos git |

### 🗺️ SLAM y localización

| Paquete | Para qué sirve |
|---------|----------------|
| `ros-jazzy-slam-toolbox` | SLAM principal (sync_slam_toolbox_node) |
| `ros-jazzy-robot-localization` | EKF para fusión IMU + odometría |
| `ros-jazzy-rplidar-ros` | Driver del LiDAR RPLIDAR A1M8 |
| `ros-jazzy-nav2-map-server` | Guardar/cargar mapas (.pgm + .yaml) |
| `ros-jazzy-nav2-lifecycle-manager` | Auto-activación de nodos lifecycle |
| `ros-jazzy-nav2-msgs` | Mensajes para Nav2 (futuro) |

### 🌳 TF y transformaciones

| Paquete | Para qué sirve |
|---------|----------------|
| `ros-jazzy-tf2-tools` | Herramientas para inspeccionar TF tree |
| `ros-jazzy-tf2-ros` | Bibliotecas de TF2 para C++/Python |
| `ros-jazzy-tf-transformations` | Conversiones quaternion ↔ Euler |
| `ros-jazzy-xacro` | Procesar URDF parametrizado (.xacro) |
| `ros-jazzy-joint-state-publisher` | Publicar estados de juntas |
| `ros-jazzy-joint-state-publisher-gui` | GUI para mover juntas en pruebas |
| `ros-jazzy-robot-state-publisher` | Publicar TF desde URDF |

### 📷 Cámara y visión

| Paquete | Para qué sirve |
|---------|----------------|
| `ros-jazzy-cv-bridge` | Conversión Image ROS ↔ OpenCV |
| `ros-jazzy-image-transport` | Transporte eficiente de imágenes |
| `ros-jazzy-image-transport-plugins` | Compresión JPEG/Theora/etc |
| `v4l-utils` | Utilidades para cámaras V4L2 |

### 🌐 Visualización y conectividad

| Paquete | Para qué sirve |
|---------|----------------|
| `ros-jazzy-foxglove-bridge` | WebSocket bridge para Foxglove Studio |
| `ros-jazzy-rmw-cyclonedds-cpp` | DDS alternativo (mejor para Tailscale) |
| `ros-jazzy-diagnostic-updater` | Diagnostics para monitoreo |

### 🎮 Teleoperación

| Paquete | Para qué sirve |
|---------|----------------|
| `ros-jazzy-teleop-twist-keyboard` | Teleop básico por teclado |

### 🔧 Sistema y compilación

| Paquete | Para qué sirve |
|---------|----------------|
| `build-essential` | gcc, g++, make |
| `cmake` | Build system |
| `git` | Control de versiones |
| `python3-pip` | Manejador de paquetes Python |
| `python3-dev` | Headers de Python para extensiones |
| `python3-setuptools` | Build de paquetes Python |
| `libudev-dev` | Headers de udev (para detectar USB) |
| `libusb-1.0-0-dev` | USB driver para LiDAR |
| `libssl-dev` | TLS/SSL (Tailscale, HTTPS) |
| `libffi-dev` | Foreign function interface |
| `libsrtp2-dev` | SRTP para WebRTC |
| `libavcodec-dev` y `libav*-dev` | FFmpeg para codificación de video |
| `libswscale-dev` | Escalado de imágenes |
| `pkg-config` | Configurar flags de compilación |

### 🐍 Python (vía pip)

| Paquete | Para qué sirve |
|---------|----------------|
| `Rosmaster_Lib` | **Driver oficial Yahboom** para STM32 (motores + IMU + voltaje) |
| `pyzmq` | ZMQ bindings — bridge con clientes externos |
| `flask` | Servidor web ligero (teleop UI) |
| `flask-cors` | CORS para API REST |
| `aiortc` | WebRTC asíncrono (versión inicial del bridge de cámara) |
| `aiohttp` | HTTP asíncrono (servidor de cámara) |
| `av` | PyAV — encoding/decoding de video |
| `numpy<2` | **Pin a numpy 1.x** — ROS2 Jazzy no es compatible con numpy 2.x |
| `opencv-python` | Procesamiento de imágenes |
| `opencv-contrib-python` | Algoritmos extras de OpenCV (SLAM, AR, etc.) |
| `transforms3d` | Conversiones de transformaciones 3D |
| `pyserial` | Comunicación serial |
| `psutil` | Información del sistema (CPU, RAM) |

### 🌐 Conectividad remota

| Software | Para qué sirve |
|----------|----------------|
| `tailscale` | VPN mesh — acceso remoto al robot desde cualquier red |

### ⚠️ Notas importantes

1. **`numpy<2`** — Este es el pin más importante. ROS2 Jazzy fue compilado con numpy 1.x. Si numpy 2.x se instala, **TODO ROS2 Python falla** con `ImportError: numpy.core.multiarray failed to import`.

2. **`Rosmaster_Lib`** — Es la biblioteca oficial de Yahboom. La versión 3.3.9 expone:
   - `bot.set_car_motion(vx, vy, wz)` — comando de movimiento
   - `bot.get_motion_data()` — velocidades reales
   - `bot.get_accelerometer_data()` — IMU acelerómetro
   - `bot.get_gyroscope_data()` — IMU giroscopio
   - `bot.get_battery_voltage()` — voltaje

3. **`aiortc + aiohttp + av`** — Aunque migramos a ZMQ, los dejamos por compatibilidad con la versión inicial WebRTC del bridge de cámara.

4. **Swap de 4GB** — Crítico para compilar SLAM Toolbox y OrbbecSDK_ROS2 en RPi5 sin OOM kills.

5. **Variables de entorno problemáticas:**
   - **NO** agregar `RMW_IMPLEMENTATION` al `.bashrc`
   - **NO** agregar `ROS_DISCOVERY_SERVER` al `.bashrc`
   Estos rompen el descubrimiento entre máquinas con Tailscale.

---

## 🇬🇧 English

### 🤖 ROS2 Jazzy (base)

Same as Spanish section — ROS2 desktop installation with development tools.

### 🗺️ SLAM and localization

Same packages — slam_toolbox (sync), robot_localization (EKF), rplidar_ros, nav2 components for map saving and lifecycle management.

### 🌳 TF and transforms

Standard TF2 tools, xacro for URDF, joint/robot state publishers.

### 📷 Camera and vision

cv_bridge, image_transport, V4L2 utilities.

### 🌐 Visualization and connectivity

foxglove_bridge, CycloneDDS, diagnostics.

### 🎮 Teleoperation

teleop_twist_keyboard.

### 🔧 System and build

Standard build tools, USB development libraries, FFmpeg for video.

### 🐍 Python (via pip)

| Package | Purpose |
|---------|---------|
| `Rosmaster_Lib` | **Official Yahboom driver** for STM32 |
| `pyzmq` | ZMQ bindings — external client bridge |
| `flask` + `flask-cors` | Web server (teleop UI) |
| `aiortc` + `aiohttp` + `av` | WebRTC stack (initial camera bridge) |
| `numpy<2` | **Pinned to 1.x** — ROS2 Jazzy incompatible with numpy 2.x |
| `opencv-python` | Image processing |
| `transforms3d` | 3D transformation conversions |
| `pyserial` | Serial communication |
| `psutil` | System info |

### 🌐 Remote connectivity

| Software | Purpose |
|----------|---------|
| `tailscale` | Mesh VPN — remote access from any network |

### ⚠️ Important notes

1. **`numpy<2` pinning** is the single most important constraint. Without it, **all ROS2 Python crashes**.

2. **`Rosmaster_Lib` 3.3.9** is required for the IMU access methods (`get_accelerometer_data`, `get_gyroscope_data`).

3. **4GB swap is critical** for compiling on RPi5 without OOM kills.

4. **Don't add `RMW_IMPLEMENTATION` or `ROS_DISCOVERY_SERVER` to `.bashrc`** — breaks Tailscale-mediated communication.

---

## 🔥 Verificación rápida / Quick verification

Después de la instalación / After installation:

```bash
# ROS2 instalado
ros2 --version

# Paquetes específicos
ros2 pkg list | grep -E "slam|rplidar|robot_localization|foxglove"

# Python deps
python3 -c "import zmq, flask, cv2, numpy, av, aiortc; print('OK')"
python3 -c "from Rosmaster_Lib import Rosmaster; print('Yahboom OK')"

# Sistema
swapon --show
free -h
```

Si todo da OK, estás listo para compilar el workspace.

If everything is OK, you're ready to build the workspace.