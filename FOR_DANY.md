# 👋 Para Dany / For Dany — Guía rápida de replicación

## 🇪🇸 ¡Hola Dany!

Esta guía es para que puedas replicar **exactamente** lo que hicimos con el robot. Sigue los pasos en orden y al final tendrás SLAM, teleop web y stream de cámara funcionando.

### Lo que necesitas tener listo

- ☑️ ROSMASTER X3 ensamblado y cargado
- ☑️ Raspberry Pi 5 (8GB)
- ☑️ Tarjeta SD con Ubuntu 24.04 LTS
- ☑️ Cable USB del LiDAR conectado
- ☑️ Cable USB del STM32 conectado
- ☑️ Internet en la RPi
- ☑️ Una PC para acceso remoto

### Tiempo estimado: 1.5 - 2 horas

### Pasos

#### 1. Clonar el repo en tu RPi

```bash
cd ~
git clone https://github.com/TU_USUARIO/ROSMASTERX3-SLAM-Stack.git
cd ROSMASTERX3-SLAM-Stack
```

#### 2. Correr el instalador

```bash
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh
```

⚠️ Esto tarda ~30 minutos. Toma un café.

#### 3. Configurar puertos USB

```bash
sudo cp config/99-rosmaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -la /dev/yahboom /dev/rplidar
```

Si ves los 2 symlinks, ✅ todo bien.

#### 4. Copiar los paquetes ROS2

```bash
mkdir -p ~/ros2_ws_02/src
cp -r src/* ~/ros2_ws_02/src/
```

#### 5. Compilar

```bash
cd ~/ros2_ws_02
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

⚠️ Esto tarda ~10 minutos.

#### 6. Configurar tu `.bashrc`

```bash
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/ros2_ws_02/install/setup.bash' >> ~/.bashrc
echo 'export ROS_DOMAIN_ID=0' >> ~/.bashrc
source ~/.bashrc
```

#### 7. Instalar Tailscale (recomendado)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled
sudo tailscale up
```

Apunta la IP que te da: `tailscale ip -4`. Esa es la IP que usarás desde tu PC.

#### 8. Probar con el robot encendido

⚠️ **AMBOS** switches del robot deben estar encendidos: el principal Y el de motores.

```bash
ros2 launch rosmaster_bringup full_stack.launch.py
```

⚠️ **NO MUEVAS el robot durante los primeros 3 segundos** — la IMU se está calibrando.

#### 9. Verificar desde tu PC

Abre tu navegador en:

- **Teleop:** `http://TU_IP_TAILSCALE:5000` ← mueve el robot con WASD+QE
- **Foxglove:** `https://app.foxglove.dev` → conecta a `ws://TU_IP_TAILSCALE:8765` → agrega panels 3D con `/scan` y `/map`

### Para mapear tu casa

1. Pon el robot en una esquina
2. Mueve **muy despacio** con teleop
3. Para 2 segundos en cada esquina del cuarto
4. **Cierra el loop** — vuelve al punto inicial
5. Guarda el mapa:
   ```bash
   mkdir -p ~/maps
   cd ~/maps
   ros2 run nav2_map_server map_saver_cli -f mi_casa
   ```

### ¿Algo no funciona?

Lee [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — están listados los errores típicos con sus soluciones.

Si tu problema no está ahí, abre un issue en GitHub o escríbeme directamente.

---

## 🇬🇧 Hi Dany!

This guide helps you replicate **exactly** what we built. Follow steps in order and you'll have SLAM, web teleop, and camera streaming working at the end.

### Estimated time: 1.5 - 2 hours

### Steps

#### 1. Clone the repo on your RPi

```bash
cd ~
git clone https://github.com/YOUR_USER/ROSMASTERX3-SLAM-Stack.git
cd ROSMASTERX3-SLAM-Stack
```

#### 2. Run the installer

```bash
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh
```

⚠️ Takes ~30 min. Get coffee.

#### 3. Set up USB ports

```bash
sudo cp config/99-rosmaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -la /dev/yahboom /dev/rplidar
```

#### 4. Copy ROS2 packages

```bash
mkdir -p ~/ros2_ws_02/src
cp -r src/* ~/ros2_ws_02/src/
```

#### 5. Build

```bash
cd ~/ros2_ws_02
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

#### 6. Configure `.bashrc`

```bash
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/ros2_ws_02/install/setup.bash' >> ~/.bashrc
echo 'export ROS_DOMAIN_ID=0' >> ~/.bashrc
source ~/.bashrc
```

#### 7. Install Tailscale (recommended)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled
sudo tailscale up
tailscale ip -4
```

#### 8. Test with the robot

⚠️ **BOTH** robot switches ON.
⚠️ **DON'T MOVE** the robot during first 3 seconds — IMU calibration.

```bash
ros2 launch rosmaster_bringup full_stack.launch.py
```

#### 9. From your PC

- **Teleop:** `http://YOUR_TAILSCALE_IP:5000`
- **Foxglove:** `https://app.foxglove.dev` → connect to `ws://YOUR_TAILSCALE_IP:8765`

### Mapping workflow

1. Place robot in a corner
2. Drive **very slowly** with teleop
3. Pause 2 seconds at each corner
4. **Close the loop** — return to start
5. Save the map:
   ```bash
   mkdir -p ~/maps && cd ~/maps
   ros2 run nav2_map_server map_saver_cli -f my_house
   ```

### Issues?

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
