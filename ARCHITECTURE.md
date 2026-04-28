# 🏗️ ARCHITECTURE — Diseño del Stack / Stack Design

## 🇪🇸 Español

### Visión general

El stack está diseñado siguiendo 3 principios:

1. **ROS2 como hub central** — toda la lógica de robótica vive en ROS2
2. **Múltiples puentes hacia afuera** — clientes externos (Unity, navegador, móvil) se conectan via protocolos estándar sin necesitar ROS
3. **Modularidad** — cada paquete hace una cosa y la hace bien

### Diagrama de flujo de datos

```
┌────────────────────────────────────────────────────────────┐
│                    HARDWARE FÍSICO                          │
│  STM32 Yahboom ◄─USB─ RPi5 ─USB─► RPLIDAR A1M8 ─USB─► Cam  │
│  └─ Motores Mecanum                                         │
│  └─ Encoders                                                │
│  └─ IMU MPU9250                                             │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                  ROS2 JAZZY (RPi5)                          │
│                                                             │
│  ┌──────────────────┐                                      │
│  │ yahboom_driver   │ /vel_raw, /imu/data_raw,            │
│  │ (50Hz)           │ /battery_voltage, /wheel_velocities  │
│  └──────────────────┘                                      │
│           │                                                 │
│           ▼ /vel_raw                                        │
│  ┌──────────────────┐                                      │
│  │ rosmaster_odom   │ /odom (10Hz)                        │
│  └──────────────────┘                                      │
│           │ + /imu/data_raw                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                      │
│  │ ekf_filter_node  │ /odometry/filtered (30Hz)           │
│  │ (robot_loc)      │ TF: odom → base_footprint           │
│  └──────────────────┘                                      │
│           │ + /scan (7Hz)                                   │
│           ▼                                                 │
│  ┌──────────────────┐                                      │
│  │ slam_toolbox     │ /map (1Hz)                          │
│  │ (sync mode)      │ TF: map → odom                      │
│  └──────────────────┘                                      │
│                                                             │
│  ENTRADA DE COMANDOS:                                       │
│  /cmd_vel_in → safety_stop → /cmd_vel_safe →               │
│  → heading_controller → /cmd_vel → yahboom_driver           │
│                                                             │
│  PUENTES HACIA AFUERA:                                     │
│  ┌──────────────┬─────────────┬──────────────┐            │
│  │  Foxglove    │  ZMQ Bridge │  Flask Web   │            │
│  │  WebSocket   │  Pub/Sub    │  HTTP        │            │
│  │  :8765       │  :5555/5001 │  :5000       │            │
│  │              │  :5002      │              │            │
│  └──────────────┴─────────────┴──────────────┘            │
└────────────────────────────────────────────────────────────┘
                       │
                       ▼ (Tailscale VPN)
┌────────────────────────────────────────────────────────────┐
│                   CLIENTES REMOTOS                          │
│                                                             │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────────┐    │
│  │  Foxglove    │  │  Browser   │  │  Quest 3 / Unity│    │
│  │  Studio      │  │  WASD UI   │  │  ZMQ + WebSocket│    │
│  └──────────────┘  └────────────┘  └─────────────────┘    │
└────────────────────────────────────────────────────────────┘
```

### Cadena de control (cmd_vel)

```
Usuario (web/Unity/teleop)
  ↓ Twist {vx, vy, wz}
/cmd_vel_in
  ↓
[safety_stop]  ← lee /scan, frena si obstáculo frontal
  ↓
/cmd_vel_safe
  ↓
[heading_controller]  ← PID con /odometry/filtered
  ↓
/cmd_vel
  ↓
[yahboom_driver]  ← cinemática inversa mecanum
  ↓
STM32 → motores
```

### TF Tree

```
map ─[slam_toolbox]→ odom ─[EKF]→ base_footprint
                                        ↓ [URDF]
                                   base_link
                                        ├─ laser_frame
                                        ├─ imu_link
                                        └─ wheel_FL/FR/RL/RR
```

### Paquetes ROS2

| Paquete | Función | Topics publicados |
|---------|---------|-------------------|
| `rosmaster_description` | URDF/Xacro del robot | `/robot_description`, `/joint_states` |
| `rosmaster_hardware` | Driver STM32 + odom + control | `/vel_raw`, `/odom`, `/imu/data_raw`, `/battery_voltage` |
| `rosmaster_slam` | SLAM Toolbox + EKF + LiDAR | `/scan`, `/map`, `/odometry/filtered` |
| `rosmaster_zmq_bridge` | Puente ROS↔ZMQ + Flask | `/cmd_vel_in` (sub), envía a ZMQ |
| `rosmaster_bringup` | Launch maestro | — |

### Puertos y protocolos

| Puerto | Protocolo | Servicio | Cliente típico |
|--------|-----------|----------|----------------|
| 5000 | HTTP | Flask teleop UI | Navegador |
| 5001 | ZMQ PUB | Sensores (lidar, odom, batt) | Python, Unity |
| 5002 | ZMQ SUB | Comandos cmd_vel | Cualquier publisher |
| 5555 | ZMQ PUB | Stream de video JPEG | Python, Unity |
| 5556 | ZMQ PUB | Stream depth (preparado) | Python, Unity |
| 8765 | WebSocket | Foxglove Bridge | Foxglove Studio |

### Decisiones de diseño clave

1. **Por qué NO usar `ros2_control`:**
   El driver Yahboom usa una API serial propietaria del STM32. Implementar `hardware_interface` añade complejidad sin beneficios reales para mecanum.

2. **Por qué `sync_slam_toolbox_node` en lugar de `async`:**
   En entornos pequeños (casas/oficinas) sync da mejor calidad de mapa al procesar cada scan completamente. La diferencia de CPU es manejable en RPi5.

3. **Por qué fusionar IMU solo con `vyaw`:**
   El acelerómetro del MPU9250 tiene bias mecánico (~0.36 m/s²) por inclinación física del robot. Fusionarlo introduce drift. El giroscopio Z, calibrado, es muy confiable.

4. **Por qué ZMQ en lugar de rosbridge:**
   ZMQ tiene latencia ~10-30ms vs ~50-100ms de rosbridge HTTP. Para Quest 3 (necesita 60+ FPS) ZMQ es la única opción viable.

5. **Por qué `imu0_relative: true`:**
   La MPU9250 no tiene magnetómetro funcional para yaw absoluto. `relative=true` toma el yaw inicial como origen y solo integra incrementos.

---

## 🇬🇧 English

### Design philosophy

Three principles:

1. **ROS2 as central hub** — all robotics logic lives in ROS2
2. **Multiple outward bridges** — external clients (Unity, browser, mobile) connect via standard protocols without needing ROS
3. **Modularity** — each package does one thing well

(Same diagrams and tables as Spanish section above.)

### Why these choices?

1. **Why NOT use `ros2_control`:** The Yahboom driver uses a proprietary STM32 serial API. Implementing `hardware_interface` adds complexity without real benefits for mecanum.

2. **Why `sync_slam_toolbox_node` over `async`:** In small environments (homes/offices) sync gives better map quality by processing each scan completely. The CPU difference is manageable on RPi5.

3. **Why fuse IMU only with `vyaw`:** The MPU9250 accelerometer has mechanical bias (~0.36 m/s²) due to physical robot tilt. Fusing it introduces drift. The Z gyro, calibrated, is very reliable.

4. **Why ZMQ instead of rosbridge:** ZMQ has ~10-30ms latency vs ~50-100ms for rosbridge HTTP. For Quest 3 (needs 60+ FPS) ZMQ is the only viable option.

5. **Why `imu0_relative: true`:** The MPU9250 doesn't have a functional magnetometer for absolute yaw. `relative=true` takes the initial yaw as origin and only integrates increments.
