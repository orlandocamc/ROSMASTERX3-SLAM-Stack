# 📖 SETUP — Instalación detallada / Detailed setup

## 🇪🇸 Español

### Prerrequisitos

- Raspberry Pi 5 (8GB recomendado)
- Ubuntu 24.04 LTS instalado
- ROSMASTER X3 ensamblado y funcionando
- Acceso a internet en la RPi

### Paso 1 — Instalar ROS2 Jazzy

```bash
# Configurar locale
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Agregar repositorio ROS2
sudo apt update && sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Instalar ROS2 Jazzy
sudo apt update
sudo apt install -y ros-jazzy-desktop python3-colcon-common-extensions python3-rosdep
sudo rosdep init
rosdep update
```

### Paso 2 — Configurar swap de 4GB

Necesario para compilar paquetes pesados en RPi:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verificar:
```bash
free -h
swapon --show
```

### Paso 3 — Instalar dependencias del proyecto

```bash
sudo apt install -y \
  ros-jazzy-slam-toolbox \
  ros-jazzy-rplidar-ros \
  ros-jazzy-robot-localization \
  ros-jazzy-foxglove-bridge \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-cv-bridge \
  ros-jazzy-nav2-map-server \
  ros-jazzy-nav2-lifecycle-manager \
  python3-pip \
  libudev-dev \
  libusb-1.0-0-dev \
  git

pip install Rosmaster_Lib aiortc aiohttp av "numpy<2" pyzmq flask --break-system-packages
```

### Paso 4 — Configurar puertos USB fijos (udev rules)

El ROSMASTER X3 tiene 2 dispositivos USB-serial:
- **STM32 (motores + IMU):** `/dev/yahboom`
- **RPLIDAR A1M8:** `/dev/rplidar`

Para que los nombres no cambien al reconectar:

```bash
sudo cp config/99-rosmaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Verificar:
```bash
ls -la /dev/yahboom /dev/rplidar
```

Debe mostrar symlinks a `/dev/ttyUSB0` y `/dev/ttyUSB1` (o similar).

### Paso 5 — Configurar Tailscale (opcional pero recomendado)

Tailscale permite acceso remoto al robot desde cualquier red:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled
sudo tailscale up
```

Anotar la IP que devuelve `tailscale ip -4` (ej. `100.90.163.4`).

### Paso 6 — Compilar el workspace

```bash
mkdir -p ~/ros2_ws_02/src
cp -r src/* ~/ros2_ws_02/src/
cd ~/ros2_ws_02

source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

Esto tarda ~5-10 minutos en la RPi5.

### Paso 7 — Configurar `.bashrc`

Agregar al final de `~/.bashrc`:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws_02/install/setup.bash
export ROS_DOMAIN_ID=0
```

Recargar:
```bash
source ~/.bashrc
```

### Paso 8 — Calibrar la IMU

El driver Yahboom calibra la IMU automáticamente al iniciar. **Importante:** mantener el robot **completamente quieto** durante los primeros 3 segundos del lanzamiento.

### Paso 9 — Lanzar el stack completo

Verificar que ambos switches del robot estén encendidos. Luego:

```bash
ros2 launch rosmaster_bringup full_stack.launch.py
```

Si la cámara está conectada y se detecta en `/dev/video0`:
```bash
ros2 launch rosmaster_bringup full_stack.launch.py video_device:=0
```

### Paso 10 — Verificar que todo funciona

En otra terminal:

```bash
# Topics activos
ros2 topic list

# Verificar IMU
ros2 topic hz /imu/data_raw      # debe ser ~50Hz

# Verificar LiDAR
ros2 topic hz /scan              # debe ser ~7Hz

# Verificar SLAM
ros2 lifecycle get /slam_toolbox  # debe decir 'active'
ros2 topic hz /map                # debe publicar a 1Hz aprox

# Verificar EKF
ros2 topic hz /odometry/filtered  # debe ser ~30Hz
```

---

## 🇬🇧 English

### Prerequisites

- Raspberry Pi 5 (8GB recommended)
- Ubuntu 24.04 LTS installed
- ROSMASTER X3 assembled and working
- Internet access on the RPi

### Step 1 — Install ROS2 Jazzy

```bash
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

sudo apt update && sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-jazzy-desktop python3-colcon-common-extensions python3-rosdep
sudo rosdep init
rosdep update
```

### Step 2 — Configure 4GB swap

Needed to compile heavy packages on RPi:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Step 3 — Install project dependencies

```bash
sudo apt install -y \
  ros-jazzy-slam-toolbox \
  ros-jazzy-rplidar-ros \
  ros-jazzy-robot-localization \
  ros-jazzy-foxglove-bridge \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-cv-bridge \
  ros-jazzy-nav2-map-server \
  ros-jazzy-nav2-lifecycle-manager \
  python3-pip libudev-dev libusb-1.0-0-dev git

pip install Rosmaster_Lib aiortc aiohttp av "numpy<2" pyzmq flask --break-system-packages
```

### Step 4 — Set up fixed USB ports (udev rules)

```bash
sudo cp config/99-rosmaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
ls -la /dev/yahboom /dev/rplidar
```

### Step 5 — Set up Tailscale (recommended)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled
sudo tailscale up
tailscale ip -4
```

### Step 6 — Build the workspace

```bash
mkdir -p ~/ros2_ws_02/src
cp -r src/* ~/ros2_ws_02/src/
cd ~/ros2_ws_02
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

### Step 7 — Configure `.bashrc`

```bash
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/ros2_ws_02/install/setup.bash' >> ~/.bashrc
echo 'export ROS_DOMAIN_ID=0' >> ~/.bashrc
source ~/.bashrc
```

### Step 8 — Launch full stack

Make sure both robot switches are ON. Keep the robot **completely still** for the first 3 seconds (IMU calibration):

```bash
ros2 launch rosmaster_bringup full_stack.launch.py
```

### Step 9 — Verify everything works

```bash
ros2 topic list
ros2 topic hz /imu/data_raw       # ~50Hz expected
ros2 topic hz /scan               # ~7Hz expected
ros2 lifecycle get /slam_toolbox  # should be 'active'
ros2 topic hz /map                # ~1Hz expected
```

---

## 🚨 Common issues / Problemas comunes

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
