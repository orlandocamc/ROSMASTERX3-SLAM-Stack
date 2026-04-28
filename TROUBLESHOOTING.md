# 🐛 TROUBLESHOOTING — Solución de problemas / Common issues

## 🇪🇸 Español

### El robot no se mueve

**Síntomas:** publicas a `/cmd_vel` pero las ruedas no giran.

**Verificar:**
1. Switches físicos del robot:
   - Switch principal: ON
   - Switch de motores: ON ⚠️ (este es el más olvidado)
2. Voltaje de batería:
   ```bash
   ros2 topic echo /battery_voltage
   ```
   Si es < 10.5V, **cargar la batería 2-4 horas**.
3. Topic correcto: el robot escucha `/cmd_vel`, no `/cmd_vel_in`. Si usas el stack completo, debes publicar a `/cmd_vel_in`.

### Puerto USB cambia (`ttyUSB0` ↔ `ttyUSB1`)

**Síntoma:** después de reconectar el robot, el LiDAR o el STM32 fallan.

**Solución:** reglas udev (incluidas en el repo):
```bash
sudo cp config/99-rosmaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -la /dev/yahboom /dev/rplidar
```

### `slam_toolbox` no genera `/map`

**Síntomas:** ves `/scan` pero `/map` no se publica.

**Verificar lifecycle:**
```bash
ros2 lifecycle get /slam_toolbox
```

Si dice `unconfigured`:
```bash
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```

Si dice `active` pero el mapa no aparece, verificar que el robot se mueva (slam_toolbox necesita movimiento para construir el mapa).

### Cámara no detectada

**Síntomas:** `client_video.py` recibe 0 frames.

**Solución:**
```bash
ls /dev/video*
```

Si la cámara está en `/dev/video1` en lugar de `/dev/video0`, lanzar con:
```bash
ros2 launch rosmaster_bringup full_stack.launch.py video_device:=1
```

### EKF reporta "No events recorded"

**Síntoma:** Foxglove muestra advertencia roja en panel Diagnostics.

**Causa típica:** el EKF se inicia ANTES que el yahboom_driver, y no recibe odom/IMU a tiempo.

**Solución:** ya está en el `slam.launch.py` — un `TimerAction` retrasa el EKF 1 segundo. Si aún ocurre, aumentar el delay.

### Robot zigzaguea al avanzar recto

**Causa:** Los robots mecanum baratos tienen ruedas no calibradas. El estimador de velocidad del STM32 reporta `wz` ruidoso (~±0.07 rad/s) incluso quieto.

**Mitigaciones:**
1. Asegurar que el `heading_controller` está activo:
   ```bash
   ros2 param get /heading_controller enable
   ```
2. Tunear ganancias:
   ```bash
   ros2 param set /heading_controller kp 1.5
   ros2 param set /heading_controller kd 0.4
   ```
3. **Aceptar el zigzag** — slam_toolbox compensa con loop closure si cierras loops al mapear.

### "queue is full" en slam_toolbox

**Síntoma:**
```
[slam_toolbox]: Message Filter dropping message: ... queue is full
```

**Causa:** RPi5 saturada. slam_toolbox no procesa scans a tiempo.

**Soluciones:**
1. Aumentar `throttle_scans` en `mapper_params.yaml`
2. Aumentar `minimum_time_interval`
3. Reducir `max_laser_range`
4. Aumentar `resolution` (celdas más grandes = menos cómputo)

### IMU reporta valores raros (bias alto)

**Síntoma:** `linear_acceleration.x` reporta valores altos en reposo (>0.2 m/s²).

**Causa:** el robot está físicamente inclinado, o no está nivelado.

**Solución:** En `ekf.yaml`, NO fusionar `ax, ay`:
```yaml
imu0_config: [false, false, false,
              false, false, false,
              false, false, false,
              false, false, true,    # solo vyaw
              false, false, false]   # NO ax, ay
```

### El robot avanza al frente pero `/odom` reporta `x` decreciente

**Causa:** signo invertido en el driver yahboom_driver (cinemática hardcodeada al revés).

**Solución:** en `_publish_telemetry` del `yahboom_driver.py`:
```python
vel_msg.linear.x = -float(motion[0])  # invertir signo
vel_msg.linear.y = -float(motion[1])
```

### Foxglove no se conecta

**Síntoma:** `Connect` queda gris o "Waiting for events".

**Verificar:**
1. Que el `foxglove_bridge` está corriendo en la RPi:
   ```bash
   ros2 topic list | grep -v /
   netstat -an | grep 8765
   ```
2. Conectividad con la RPi:
   ```bash
   ping IP_DEL_ROBOT
   ```
3. URL correcta en Foxglove: `ws://IP:8765` (no `wss://`)

### Tailscale bloquea topics ROS2 entre máquinas

**Síntoma:** la PC no ve topics de la RPi aunque el `ROS_DOMAIN_ID` coincida.

**Causa:** Tailscale no permite multicast, que es como ROS2 descubre nodos por defecto.

**Solución:** Usar Foxglove Bridge o ZMQ en lugar de comunicar via topics ROS2 cross-machine.

### Errores de imports de numpy/scipy al lanzar

**Síntoma:**
```
ImportError: numpy.core.multiarray failed to import
```

**Causa:** numpy 2.x no es compatible con paquetes ROS2 compilados con numpy 1.x.

**Solución:**
```bash
pip install "numpy<2" --break-system-packages --force-reinstall
```

---

## 🇬🇧 English

### Robot doesn't move

**Symptoms:** publishing to `/cmd_vel` but wheels don't spin.

**Check:**
1. Physical switches:
   - Main: ON
   - Motors: ON ⚠️ (most often forgotten)
2. Battery voltage:
   ```bash
   ros2 topic echo /battery_voltage
   ```
   If < 10.5V, **charge for 2-4 hours**.
3. Correct topic: robot listens to `/cmd_vel`, not `/cmd_vel_in`. With full stack, publish to `/cmd_vel_in`.

### USB port changes (`ttyUSB0` ↔ `ttyUSB1`)

**Symptom:** after reconnecting, LiDAR or STM32 fail.

**Fix:** udev rules (included in the repo):
```bash
sudo cp config/99-rosmaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### `slam_toolbox` doesn't generate `/map`

**Check lifecycle state:**
```bash
ros2 lifecycle get /slam_toolbox
```

If `unconfigured`, manually transition:
```bash
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```

### Camera not detected

```bash
ls /dev/video*
```

If camera is on `/dev/video1`:
```bash
ros2 launch rosmaster_bringup full_stack.launch.py video_device:=1
```

### Robot zigzags while going straight

**Cause:** Cheap mecanum wheels have uncalibrated motors. STM32's velocity estimator reports noisy `wz` (~±0.07 rad/s) even at rest.

**Mitigations:**
1. Ensure `heading_controller` is active
2. Tune gains: `kp=1.5, kd=0.4`
3. **Accept it** — slam_toolbox compensates via loop closure

### "queue is full" in slam_toolbox

**Cause:** RPi5 saturated.

**Fixes:** increase `throttle_scans`, `minimum_time_interval`, or `resolution` in `mapper_params.yaml`.

### IMU reports weird values (high bias)

**Cause:** robot is physically tilted.

**Fix:** Don't fuse `ax, ay` in `ekf.yaml`, only `vyaw`.

### Robot moves forward but `/odom` shows decreasing `x`

**Cause:** sign inverted in yahboom_driver.

**Fix:** in `_publish_telemetry`:
```python
vel_msg.linear.x = -float(motion[0])
vel_msg.linear.y = -float(motion[1])
```

### Foxglove won't connect

**Check:**
1. `foxglove_bridge` running:
   ```bash
   netstat -an | grep 8765
   ```
2. URL is `ws://IP:8765` (not `wss://`)

### Tailscale blocks cross-machine ROS2 topics

**Cause:** Tailscale doesn't support multicast (ROS2 default discovery).

**Fix:** Use Foxglove Bridge or ZMQ instead of cross-machine ROS2 topics.

### numpy import errors

**Fix:**
```bash
pip install "numpy<2" --break-system-packages --force-reinstall
```
