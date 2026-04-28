#!/usr/bin/env python3
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

_ANGULAR_SLEW_LIMIT = 0.05   # rad/s máximo de cambio por tick a 50 Hz
_LINEAR_SLEW_LIMIT  = 0.02   # m/s máximo de cambio por tick a 50 Hz (aprox 1.0 m/s^2)


def _yaw_from_odom(msg: Odometry) -> float:
    q = msg.pose.pose.orientation
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def _angle_diff(a: float, b: float) -> float:
    """Diferencia angular mínima a - b en [-π, π]."""
    d = a - b
    while d > math.pi:
        d -= 2.0 * math.pi
    while d < -math.pi:
        d += 2.0 * math.pi
    return d


class HeadingController(Node):

    def __init__(self):
        super().__init__('heading_controller')

        # Te sugiero bajar un poco el KP y subir el KD para evitar oscilaciones en el X3
        self.declare_parameter('kp',                    0.8) 
        self.declare_parameter('ki',                    0.0)
        self.declare_parameter('kd',                    0.6)
        self.declare_parameter('max_angular_correction', 1.0)
        self.declare_parameter('deadband',              0.05)
        self.declare_parameter('enable',                True)
        self.declare_parameter('input_topic',           '/cmd_vel_safe')
        self.declare_parameter('output_topic',          '/cmd_vel')
        self.declare_parameter('odom_topic',            '/odometry/filtered')

        self._kp      = self.get_parameter('kp').value
        self._ki      = self.get_parameter('ki').value
        self._kd      = self.get_parameter('kd').value
        self._max_cor = self.get_parameter('max_angular_correction').value
        self._db      = self.get_parameter('deadband').value
        self._enable  = self.get_parameter('enable').value
        in_topic      = self.get_parameter('input_topic').value
        out_topic     = self.get_parameter('output_topic').value
        odom_topic    = self.get_parameter('odom_topic').value

        self._pub = self.create_publisher(Twist, out_topic, 10)
        self.create_subscription(Twist,    in_topic,   self._cmd_cb,  10)
        self.create_subscription(Odometry, odom_topic, self._odom_cb, 10)

        # Último comando recibido
        self._last_cmd:      Twist | None = None
        self._last_cmd_time: float        = time.monotonic()

        # Yaw actual
        self._yaw: float | None = None

        # Estado PID y suavizado
        self._setpoint:  float | None = None
        self._integral:  float        = 0.0
        self._prev_err:  float        = 0.0
        self._prev_time: float        = time.monotonic()
        
        # Guardamos las velocidades anteriores para aplicar las rampas
        self._prev_wz:   float        = 0.0   
        self._prev_vx:   float        = 0.0   
        self._mode:      str          = 'giro libre'

        self._log_count:      int  = 0
        self._no_odom_warned: bool = False

        self.create_timer(1.0 / 50.0, self._control_cb)

        self.get_logger().info(
            f"HeadingController listo — kp={self._kp} ki={self._ki} kd={self._kd} "
            f"db={self._db} enable={self._enable} "
            f"{in_topic} → {out_topic} @ 50 Hz"
        )

    def _odom_cb(self, msg: Odometry):
        self._yaw = _yaw_from_odom(msg)

    def _cmd_cb(self, msg: Twist):
        self._last_cmd = msg
        self._last_cmd_time = time.monotonic()

    def _control_cb(self):
        cmd = self._last_cmd
        now = time.monotonic()

        # Metas deseadas (por defecto 0)
        target_vx = 0.0
        target_wz = 0.0

        # Watchdog: Si no hay comando fresco, las metas son 0 (frenado suave)
        if cmd is None or (now - self._last_cmd_time > 0.5):
            if self._mode != 'parado':
                self._mode = 'parado'
                self._reset_pid()
                self.get_logger().info("modo: parado (watchdog o sin comando)")
        else:
            if not self._enable:
                self._pub.publish(cmd)
                return

            target_vx = cmd.linear.x
            target_wz = cmd.angular.z

            moving_linear = abs(target_vx) > 1e-6
            rotating      = abs(target_wz) >= self._db
            fully_stopped = not moving_linear and not rotating

            if fully_stopped:
                if self._mode != 'parado':
                    self._mode = 'parado'
                    self.get_logger().info("modo: parado")
                self._reset_pid()

            elif rotating:
                if self._mode != 'giro libre':
                    self._mode = 'giro libre'
                    self.get_logger().info("modo: giro libre")
                self._reset_pid()
                # Pasamos el giro tal cual al target
                pass 

            elif moving_linear:
                if self._yaw is None:
                    if not self._no_odom_warned:
                        self._no_odom_warned = True
                        self.get_logger().warn("Esperando odometry...")
                else:
                    self._no_odom_warned = False
                    if self._mode != 'recto':
                        self._mode     = 'recto'
                        self._setpoint = self._yaw
                        self._integral = 0.0
                        self._prev_err = 0.0
                        self._prev_time = time.monotonic()
                        self.get_logger().info(f"modo: recto — setpoint={math.degrees(self._setpoint):.1f}°")
                    
                    # Sobrescribimos el target_wz con la corrección del PID
                    target_wz = self._pid_step()

        # ── APLICACIÓN DE RAMPAS (SLEW RATES) PARA FRENADO/ARRANQUE SUAVE ──

        # Suavizado Lineal (vx)
        delta_vx = target_vx - self._prev_vx
        delta_vx = max(-_LINEAR_SLEW_LIMIT, min(_LINEAR_SLEW_LIMIT, delta_vx))
        out_vx = self._prev_vx + delta_vx
        self._prev_vx = out_vx

        # Suavizado Angular (wz)
        delta_wz = target_wz - self._prev_wz
        delta_wz = max(-_ANGULAR_SLEW_LIMIT, min(_ANGULAR_SLEW_LIMIT, delta_wz))
        out_wz = self._prev_wz + delta_wz
        self._prev_wz = out_wz

        # Construir y publicar el Twist final
        out = Twist()
        out.linear.x = out_vx
        if cmd is not None:
            out.linear.y = cmd.linear.y
            out.linear.z = cmd.linear.z
            out.angular.x = cmd.angular.x
            out.angular.y = cmd.angular.y
        out.angular.z = out_wz

        self._pub.publish(out)

    def _pid_step(self) -> float:
        if self._setpoint is None or self._yaw is None:
            return 0.0

        now = time.monotonic()
        dt  = now - self._prev_time
        if dt < 1e-6:
            dt = 1e-6
        self._prev_time = now

        err = _angle_diff(self._setpoint, self._yaw)
        self._integral = max(-0.5, min(0.5, self._integral + err * dt))
        deriv = (err - self._prev_err) / dt
        self._prev_err = err

        raw     = self._kp * err + self._ki * self._integral + self._kd * deriv
        clamped = max(-self._max_cor, min(self._max_cor, raw))
        
        return clamped

    def _reset_pid(self):
        self._setpoint  = None
        self._integral  = 0.0
        self._prev_err  = 0.0
        self._prev_time = time.monotonic()


def main(args=None):
    rclpy.init(args=args)
    node = HeadingController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()