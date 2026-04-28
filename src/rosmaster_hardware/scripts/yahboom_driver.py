#!/usr/bin/env python3
"""
yahboom_driver.py

Driver ROS2 para el ROSMASTER X3 usando Rosmaster_Lib.

Tópicos publicados:
  /wheel_velocities  std_msgs/Float32MultiArray  — vx, vy, vz desde get_motion_data()
  /battery_voltage   std_msgs/Float32            — voltaje en V

Tópicos suscritos:
  /cmd_vel  geometry_msgs/Twist  — velocidad de referencia

Parámetros:
  port  (string, default '/dev/ttyUSB0')
"""

import math
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32, Float32MultiArray

try:
    from Rosmaster_Lib import Rosmaster
except ImportError:
    raise SystemExit('Rosmaster_Lib no encontrada. Instala el paquete Yahboom.')

# Número de muestras y periodo para la calibración (50 Hz × 3 s)
_CAL_SAMPLES = 150
_CAL_DT      = 0.02


class YahboomDriver(Node):

    def __init__(self):
        super().__init__('yahboom_driver')

        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('acceleration_limit',         1.0)   # m/s²
        self.declare_parameter('angular_acceleration_limit', 2.0)   # rad/s²
        port           = self.get_parameter('port').value
        self._acc_lin  = self.get_parameter('acceleration_limit').value
        self._acc_ang  = self.get_parameter('angular_acceleration_limit').value

        # ── Inicializar robot ─────────────────────────────────────────────
        self._bot = Rosmaster(car_type=1, com=port)
        self._bot.create_receive_threading()
        self.get_logger().info(f'Rosmaster_Lib iniciada — puerto: {port}')

        # ── Calibración IMU (bloquea ~3 s antes de arrancar los timers) ───
        self._calibrate_imu()

        # ── Publishers ────────────────────────────────────────────────────
        self._pub_wheels  = self.create_publisher(
            Float32MultiArray, '/wheel_velocities', 10)
        self._pub_battery = self.create_publisher(
            Float32, '/battery_voltage', 10)
        self._pub_vel_raw = self.create_publisher(
            Twist, '/vel_raw', 10)
        self._pub_imu     = self.create_publisher(
            Imu, '/imu/data_raw', 10)

        # ── Subscriber ───────────────────────────────────────────────────
        self.create_subscription(Twist, '/cmd_vel', self._cmd_vel_cb, 10)

        # ── Estado rampa de velocidad ─────────────────────────────────────
        # _tgt: velocidad objetivo (se actualiza en cmd_vel_cb / watchdog)
        # _cur: velocidad actualmente enviada al hardware (interpolada)
        self._tgt: list[float] = [0.0, 0.0, 0.0]   # [vx, vy, wz]
        self._cur: list[float] = [0.0, 0.0, 0.0]

        # ── Watchdog: tiempo del último cmd_vel ───────────────────────────
        self._last_cmd_time    = self.get_clock().now()
        self._watchdog_timeout = 1.0   # segundos
        self._moving           = False

        # ── Timers ────────────────────────────────────────────────────────
        self.create_timer(0.1,  self._publish_telemetry)   # 10 Hz
        self.create_timer(0.1,  self._watchdog_cb)          # 10 Hz
        self.create_timer(0.02, self._publish_imu)          # 50 Hz
        self.create_timer(0.02, self._ramp_cb)              # 50 Hz

    # ── Calibración IMU ────────────────────────────────────────────────────

    def _calibrate_imu(self):
        """
        Recoge _CAL_SAMPLES a ~50 Hz con el robot en reposo.
        Aplica la misma inversión de ejes que _publish_imu() antes de
        calcular el bias, de modo que el bias ya está en el marco corregido.
        """
        self.get_logger().info(
            "Calibrando IMU — NO MOVER el robot por 3 segundos...")

        samples_g: list[tuple] = []
        samples_a: list[tuple] = []

        for _ in range(_CAL_SAMPLES):
            g = self._bot.get_gyroscope_data()
            a = self._bot.get_accelerometer_data()

            if g is not None:
                # Aplicar la misma inversión de ejes que en _publish_imu
                gx, gy, gz = -float(g[0]), float(g[1]), -float(g[2])
                samples_g.append((gx, gy, gz))

            if a is not None:
                ax, ay, az = -float(a[0]), float(a[1]), -float(a[2])
                samples_a.append((ax, ay, az))

            time.sleep(_CAL_DT)

        if samples_g:
            n = len(samples_g)
            self._bias_gx = sum(s[0] for s in samples_g) / n
            self._bias_gy = sum(s[1] for s in samples_g) / n
            self._bias_gz = sum(s[2] for s in samples_g) / n
        else:
            self._bias_gx = self._bias_gy = self._bias_gz = 0.0

        if samples_a:
            n = len(samples_a)
            self._bias_ax = sum(s[0] for s in samples_a) / n
            self._bias_ay = sum(s[1] for s in samples_a) / n
            # az no se corrige: incluye gravedad (+9.81 en reposo plano)
        else:
            self._bias_ax = self._bias_ay = 0.0

        self.get_logger().info(
            f"IMU calibrada ({len(samples_g)} muestras gyro, {len(samples_a)} muestras accel) — "
            f"bias gyro: gx={self._bias_gx:.4f} gy={self._bias_gy:.4f} gz={self._bias_gz:.4f} "
            f"bias accel: ax={self._bias_ax:.4f} ay={self._bias_ay:.4f}"
        )

    # ── Callback /cmd_vel ──────────────────────────────────────────────────

    def _cmd_vel_cb(self, msg: Twist):
        self._last_cmd_time = self.get_clock().now()
        self._tgt = [msg.linear.x, msg.linear.y, msg.angular.z]
        if any(v != 0.0 for v in self._tgt):
            self._moving = True
        self.get_logger().debug(
            f'target → vx={msg.linear.x:.3f} vy={msg.linear.y:.3f} wz={msg.angular.z:.3f}')

    # ── Watchdog ───────────────────────────────────────────────────────────

    def _watchdog_cb(self):
        elapsed = (self.get_clock().now() - self._last_cmd_time).nanoseconds * 1e-9
        if elapsed > self._watchdog_timeout and self._moving:
            self._tgt = [0.0, 0.0, 0.0]   # frenado suave vía rampa
            self.get_logger().warn(
                f'Watchdog: sin cmd_vel desde {elapsed:.2f}s — frenado suave')

    # ── Rampa de aceleración 50 Hz ─────────────────────────────────────────

    def _ramp_cb(self):
        _DT        = 0.02
        lin_step   = self._acc_lin * _DT   # máx. variación linear por tick
        ang_step   = self._acc_ang * _DT   # máx. variación angular por tick
        steps      = [lin_step, lin_step, ang_step]

        changed = False
        for i in range(3):
            diff = self._tgt[i] - self._cur[i]
            if abs(diff) <= steps[i]:
                new_val = self._tgt[i]
            else:
                new_val = self._cur[i] + math.copysign(steps[i], diff)
            if new_val != self._cur[i]:
                self._cur[i] = new_val
                changed = True

        if changed or self._moving:
            self._bot.set_car_motion(self._cur[0], self._cur[1], self._cur[2])
            self._moving = any(v != 0.0 for v in self._cur)

    # ── Publicación de telemetría ──────────────────────────────────────────

    def _publish_telemetry(self):
        # Velocidades
        motion = self._bot.get_motion_data()
        if motion is not None:
            wheels_msg = Float32MultiArray()
            wheels_msg.data = [float(v) for v in motion]
            self._pub_wheels.publish(wheels_msg)

            vel_msg = Twist()
            vel_msg.linear.x  = -float(motion[0])
            vel_msg.linear.y  = -float(motion[1])
            vel_msg.angular.z = float(motion[2])
            self._pub_vel_raw.publish(vel_msg)

        # Batería
        voltage = self._bot.get_battery_voltage()
        if voltage is not None:
            bat_msg = Float32()
            bat_msg.data = float(voltage)
            self._pub_battery.publish(bat_msg)

    # ── Publicación IMU 50 Hz ─────────────────────────────────────────────

    def _publish_imu(self):
        accel = self._bot.get_accelerometer_data()
        gyro  = self._bot.get_gyroscope_data()
        if accel is None or gyro is None:
            return

        # 1) Invertir ejes: chip montado boca abajo → X y Z se invierten, Y igual
        ax = -float(accel[0])
        ay =  float(accel[1])
        az = -float(accel[2])
        gx = -float(gyro[0])
        gy =  float(gyro[1])
        gz = -float(gyro[2])

        # 2) Restar bias de gyro (accel no se corrige: el EKF no usa ax/ay)
        gx -= self._bias_gx
        gy -= self._bias_gy
        gz -= self._bias_gz

        msg = Imu()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = 'imu_link'

        # Orientación desconocida — solo rates + acelerómetro
        msg.orientation.w          = 1.0
        msg.orientation_covariance = [-1.0, 0.0, 0.0,
                                       0.0, 0.0, 0.0,
                                       0.0, 0.0, 0.0]

        msg.angular_velocity.x = gx
        msg.angular_velocity.y = gy
        msg.angular_velocity.z = gz
        msg.angular_velocity_covariance = [0.1, 0.0, 0.0,
                                           0.0, 0.1, 0.0,
                                           0.0, 0.0, 0.1]

        msg.linear_acceleration.x = ax
        msg.linear_acceleration.y = ay
        msg.linear_acceleration.z = az
        msg.linear_acceleration_covariance = [0.5, 0.0, 0.0,
                                              0.0, 0.5, 0.0,
                                              0.0, 0.0, 0.5]

        self._pub_imu.publish(msg)

    # ── Destructor ─────────────────────────────────────────────────────────

    def destroy_node(self):
        self._bot.set_car_motion(0, 0, 0)
        self.get_logger().info('Robot detenido')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = YahboomDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
