#!/bin/bash
# install_dependencies.sh
# Instala todas las dependencias necesarias para ROSMASTERX3-SLAM-Stack
# Usage: chmod +x install_dependencies.sh && ./install_dependencies.sh

set -e  # exit on error

echo "============================================"
echo "  ROSMASTERX3-SLAM-Stack — Install Script  "
echo "============================================"
echo ""

# ── 1. Verificar que estamos en Ubuntu 24.04 ──
if ! grep -q "24.04" /etc/os-release; then
    echo "⚠️  WARNING: Este script está probado en Ubuntu 24.04 LTS."
    read -p "¿Continuar de todas formas? [y/N] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

# ── 2. Verificar que ROS2 Jazzy está instalado ──
if [ ! -f /opt/ros/jazzy/setup.bash ]; then
    echo "❌ ROS2 Jazzy no encontrado. Instalándolo primero..."
    
    sudo locale-gen en_US en_US.UTF-8
    sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
    
    sudo apt update && sudo apt install -y software-properties-common curl
    sudo add-apt-repository universe -y
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    
    sudo apt update
    sudo apt install -y ros-jazzy-desktop python3-colcon-common-extensions python3-rosdep
    sudo rosdep init || true
    rosdep update
fi

echo "✅ ROS2 Jazzy detectado"

# ── 3. Configurar swap ──
if ! swapon --show | grep -q "/swapfile"; then
    echo "📦 Configurando swap de 4GB..."
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✅ Swap configurado"
else
    echo "✅ Swap ya configurado"
fi

# ── 4. Instalar dependencias ROS2 ──
echo "📦 Instalando dependencias ROS2..."
sudo apt update
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

# ── 5. Instalar paquetes Python ──
echo "🐍 Instalando paquetes Python..."
pip install Rosmaster_Lib aiortc aiohttp av "numpy<2" pyzmq flask --break-system-packages

echo ""
echo "============================================"
echo "  ✅ Instalación completada"
echo "============================================"
echo ""
echo "Siguientes pasos:"
echo ""
echo "1. Configurar reglas udev:"
echo "   sudo cp config/99-rosmaster.rules /etc/udev/rules.d/"
echo "   sudo udevadm control --reload-rules && sudo udevadm trigger"
echo ""
echo "2. Copiar paquetes ROS2 al workspace:"
echo "   mkdir -p ~/ros2_ws_02/src"
echo "   cp -r src/* ~/ros2_ws_02/src/"
echo ""
echo "3. Compilar:"
echo "   cd ~/ros2_ws_02"
echo "   source /opt/ros/jazzy/setup.bash"
echo "   colcon build --symlink-install"
echo ""
echo "4. Lanzar:"
echo "   source install/setup.bash"
echo "   ros2 launch rosmaster_bringup full_stack.launch.py"
echo ""
