#!/bin/bash
# install_dependencies.sh
# Instala TODAS las dependencias para ROSMASTERX3-SLAM-Stack
# Probado en: Raspberry Pi 5 + Ubuntu 24.04 LTS + ROS2 Jazzy
# Usage: chmod +x install_dependencies.sh && ./install_dependencies.sh

set -e
trap 'echo "❌ Error en línea $LINENO. Abortando."; exit 1' ERR

echo "================================================"
echo "  ROSMASTERX3-SLAM-Stack — Full Install Script  "
echo "================================================"
echo ""

# ── 1. Verificar sistema ──────────────────────────────
echo "📋 Paso 1/8 — Verificando sistema..."
if ! grep -q "24.04" /etc/os-release; then
    echo "⚠️  WARNING: Probado en Ubuntu 24.04 LTS."
    read -p "¿Continuar? [y/N] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

# Detectar arquitectura
ARCH=$(uname -m)
echo "   Arquitectura: $ARCH"

# ── 2. Instalar ROS2 Jazzy ────────────────────────────
echo ""
echo "📋 Paso 2/8 — ROS2 Jazzy..."
if [ ! -f /opt/ros/jazzy/setup.bash ]; then
    echo "   Instalando ROS2 Jazzy..."
    
    sudo locale-gen en_US en_US.UTF-8
    sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
    
    sudo apt update
    sudo apt install -y software-properties-common curl gnupg lsb-release
    sudo add-apt-repository universe -y
    
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg
    
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | \
        sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    
    sudo apt update
    sudo apt install -y \
        ros-jazzy-desktop \
        ros-dev-tools \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-vcstool
    
    sudo rosdep init || true
    rosdep update
    echo "   ✅ ROS2 Jazzy instalado"
else
    echo "   ✅ ROS2 Jazzy ya instalado"
fi

# ── 3. Configurar swap ────────────────────────────────
echo ""
echo "📋 Paso 3/8 — Swap de 4GB..."
if ! swapon --show | grep -q "/swapfile"; then
    echo "   Creando /swapfile..."
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
    fi
    echo "   ✅ Swap activado (persistente)"
else
    echo "   ✅ Swap ya configurado"
fi

# ── 4. Dependencias del sistema ───────────────────────
echo ""
echo "📋 Paso 4/8 — Dependencias del sistema (apt)..."
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    nano \
    htop \
    tree \
    net-tools \
    python3-pip \
    python3-dev \
    python3-setuptools \
    libudev-dev \
    libusb-1.0-0-dev \
    libssl-dev \
    libffi-dev \
    libsrtp2-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavformat-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    v4l-utils

echo "   ✅ Dependencias del sistema OK"

# ── 5. Paquetes ROS2 específicos ──────────────────────
echo ""
echo "📋 Paso 5/8 — Paquetes ROS2..."
sudo apt install -y \
    ros-jazzy-slam-toolbox \
    ros-jazzy-rplidar-ros \
    ros-jazzy-robot-localization \
    ros-jazzy-foxglove-bridge \
    ros-jazzy-teleop-twist-keyboard \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    ros-jazzy-image-transport-plugins \
    ros-jazzy-nav2-map-server \
    ros-jazzy-nav2-lifecycle-manager \
    ros-jazzy-nav2-msgs \
    ros-jazzy-tf2-tools \
    ros-jazzy-tf2-ros \
    ros-jazzy-tf-transformations \
    ros-jazzy-xacro \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-diagnostic-updater

echo "   ✅ Paquetes ROS2 instalados"

# ── 6. Paquetes Python ────────────────────────────────
echo ""
echo "📋 Paso 6/8 — Paquetes Python..."

# Bibliotecas Yahboom (driver del robot)
pip install Rosmaster_Lib --break-system-packages

# WebRTC + streaming (cámara)
pip install \
    aiortc \
    aiohttp \
    av \
    "numpy<2" \
    --break-system-packages

# ZMQ + Flask (puente con clientes externos)
pip install \
    pyzmq \
    flask \
    flask-cors \
    --break-system-packages

# Visión y procesamiento (OpenCV ya viene con ROS2 cv_bridge, pero por si acaso)
pip install \
    opencv-python \
    opencv-contrib-python \
    --break-system-packages

# Utilidades adicionales
pip install \
    transforms3d \
    pyserial \
    psutil \
    --break-system-packages

echo "   ✅ Paquetes Python instalados"

# ── 7. Tailscale (opcional pero recomendado) ──────────
echo ""
echo "📋 Paso 7/8 — Tailscale (acceso remoto)..."
if ! command -v tailscale &> /dev/null; then
    echo "   ¿Quieres instalar Tailscale para acceso remoto al robot?"
    read -p "   [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z "$REPLY" ]]; then
        curl -fsSL https://tailscale.com/install.sh | sh
        sudo systemctl enable --now tailscaled
        echo ""
        echo "   ⚠️  Para activar Tailscale corre después:"
        echo "      sudo tailscale up"
        echo ""
        echo "   Anota la IP que te da: tailscale ip -4"
        echo "   ✅ Tailscale instalado"
    else
        echo "   ⏭️  Tailscale omitido"
    fi
else
    echo "   ✅ Tailscale ya instalado"
fi

# ── 8. Configurar .bashrc ─────────────────────────────
echo ""
echo "📋 Paso 8/8 — Configurando .bashrc..."

BASHRC_LINES=(
    "source /opt/ros/jazzy/setup.bash"
    "export ROS_DOMAIN_ID=0"
)

for line in "${BASHRC_LINES[@]}"; do
    if ! grep -qF "$line" ~/.bashrc; then
        echo "$line" >> ~/.bashrc
        echo "   Agregado: $line"
    fi
done

# El source del workspace lo agregamos solo si existe
if [ -d "$HOME/ros2_ws_02/install" ]; then
    WS_SOURCE="source $HOME/ros2_ws_02/install/setup.bash"
    if ! grep -qF "$WS_SOURCE" ~/.bashrc; then
        echo "$WS_SOURCE" >> ~/.bashrc
        echo "   Agregado: $WS_SOURCE"
    fi
fi

echo "   ✅ .bashrc configurado"

# ── Resumen final ─────────────────────────────────────
echo ""
echo "================================================"
echo "  ✅ Instalación completada exitosamente"
echo "================================================"
echo ""
echo "📦 Resumen de lo instalado:"
echo "   • ROS2 Jazzy (desktop)"
echo "   • Swap de 4GB (persistente)"
echo "   • SLAM Toolbox + Robot Localization + RPLIDAR"
echo "   • Foxglove Bridge para visualización remota"
echo "   • Bibliotecas Python (ZMQ, Flask, aiortc, etc.)"
echo "   • Tailscale (si fue elegido)"
echo ""
echo "🚀 Siguientes pasos:"
echo ""
echo "   1. Configurar reglas udev:"
echo "      sudo cp config/99-rosmaster.rules /etc/udev/rules.d/"
echo "      sudo udevadm control --reload-rules && sudo udevadm trigger"
echo ""
echo "   2. Copiar paquetes ROS2 al workspace:"
echo "      mkdir -p ~/ros2_ws_02/src"
echo "      cp -r src/* ~/ros2_ws_02/src/"
echo ""
echo "   3. Compilar (~10 min en RPi5):"
echo "      cd ~/ros2_ws_02"
echo "      source /opt/ros/jazzy/setup.bash"
echo "      colcon build --symlink-install"
echo ""
echo "   4. Recargar terminal:"
echo "      source ~/.bashrc"
echo ""
echo "   5. Lanzar todo:"
echo "      ros2 launch rosmaster_bringup full_stack.launch.py"
echo ""
echo "📖 Si algo falla, lee TROUBLESHOOTING.md"
echo ""