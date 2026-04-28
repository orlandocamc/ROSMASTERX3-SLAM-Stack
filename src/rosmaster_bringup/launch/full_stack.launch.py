"""
full_stack.launch.py — Stack completo ROSMASTER X3
====================================================
Arranca en orden:
  t=0  slam.launch.py  (RSP, JSP, yahboom_driver, rosmaster_odom,
                         rplidar, EKF, slam_toolbox)
  t=0  zmq_bridge.launch.py  (video PUB, sensors PUB, cmd SUB, Flask teleop)
  t=0  foxglove_bridge  (WebSocket :8765)
  t=5  ros2 lifecycle set /slam_toolbox configure
  t=6  ros2 lifecycle set /slam_toolbox activate

Uso:
    ros2 launch rosmaster_bringup full_stack.launch.py
    ros2 launch rosmaster_bringup full_stack.launch.py video_device:=1
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_slam   = get_package_share_directory('rosmaster_slam')
    pkg_bridge = get_package_share_directory('rosmaster_zmq_bridge')

    # ── Argumentos ──────────────────────────────────────────────────────────
    video_device_arg = DeclareLaunchArgument(
        'video_device',
        default_value='0',
        description='Índice del dispositivo V4L2 para la cámara RGB',
    )

    # ── 1. Stack SLAM (driver + lidar + EKF + slam_toolbox) ─────────────────
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([pkg_slam, '/launch/slam.launch.py']),
    )

    # ── 2. ZMQ Bridge (video + sensores + cmd_vel + Flask teleop) ───────────
    zmq_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([pkg_bridge, '/launch/zmq_bridge.launch.py']),
        launch_arguments={'video_device': LaunchConfiguration('video_device')}.items(),
    )

    # ── 3. Foxglove Bridge ───────────────────────────────────────────────────
    foxglove_node = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        name='foxglove_bridge',
        output='screen',
        parameters=[{'port': 8765}],
    )

    # ── 4. Auto-activación slam_toolbox via lifecycle CLI ────────────────────
    # slam_toolbox arranca en estado "unconfigured" cuando se lanza como Node
    # (no LifecycleNode). Los dos comandos lo llevan a "active".
    # Se usan "|| true" para que no aborte si ya estuviera activo.
    slam_configure = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=['bash', '-c',
                     'ros2 lifecycle set /slam_toolbox configure || true'],
                output='screen',
            ),
        ],
    )

    slam_activate = TimerAction(
        period=6.0,
        actions=[
            ExecuteProcess(
                cmd=['bash', '-c',
                     'ros2 lifecycle set /slam_toolbox activate || true'],
                output='screen',
            ),
        ],
    )

    return LaunchDescription([
        video_device_arg,
        slam_launch,
        zmq_launch,
        foxglove_node,
        slam_configure,
        slam_activate,
    ])
