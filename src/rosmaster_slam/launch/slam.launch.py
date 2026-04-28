"""
slam.launch.py  —  Stack SLAM completo para ROSMASTER X3
=========================================================

Lanzar en lugar de robot.launch.py cuando se quiere construir un mapa:

    ros2 launch rosmaster_slam slam.launch.py

Árbol TF resultante:
    map ─[slam_toolbox]─> odom ─[EKF]─> base_footprint ─[URDF]─> base_link ─[URDF]─> laser_frame

Nodos levantados:
  1. robot_state_publisher   — TF estático del robot (URDF)
  2. joint_state_publisher   — estados de articulaciones para RViz
  3. yahboom_driver          — driver STM32 Yahboom via Rosmaster_Lib
  4. rosmaster_odom          — /odom sin TF (EKF toma el relevo)
  5. rplidar_node            — RPLIDAR A1M8, /dev/rplidar, 115200 baud
  6. ekf_filter_node         — robot_localization EKF: /odom → /odometry/filtered + TF odom→base_footprint
  7. sync_slam_toolbox_node  — slam_toolbox online_sync: /scan + TF → TF map→odom + /map
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    pkg_description = get_package_share_directory('rosmaster_description')
    pkg_slam        = get_package_share_directory('rosmaster_slam')

    ekf_config    = os.path.join(pkg_slam, 'config', 'ekf.yaml')
    mapper_config = os.path.join(pkg_slam, 'config', 'mapper_params.yaml')

    # ── Argumentos ──────────────────────────────────────────────────────
    port_arg = DeclareLaunchArgument(
        'port', default_value='/dev/yahboom',
        description='Puerto serial STM32 Yahboom'
    )
    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/rplidar',
        description='Puerto serial RPLIDAR A1M8'
    )

    # ── 1. robot_state_publisher ─────────────────────────────────────────
    xacro_file = os.path.join(pkg_description, 'urdf', 'rosmaster_x3.urdf.xacro')
    robot_description_content = ParameterValue(
        Command(['xacro ', xacro_file, ' use_sim:=false']),
        value_type=str,
    )
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_content}],
    )

    # ── 2. joint_state_publisher ─────────────────────────────────────────
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
    )

    # ── 3. yahboom_driver ───────────────────────────────────────────────
    yahboom_driver = Node(
        package='rosmaster_hardware',
        executable='yahboom_driver.py',
        name='yahboom_driver',
        output='screen',
        parameters=[{'port': LaunchConfiguration('port')}],
    )

    # ── 4. rosmaster_odom (sin TF — el EKF gestiona odom→base_footprint) ─
    rosmaster_odom = Node(
        package='rosmaster_hardware',
        executable='rosmaster_odom.py',
        name='rosmaster_odom',
        output='screen',
        parameters=[{
            'port':       LaunchConfiguration('port'),
            'publish_tf': False,           # EKF toma el relevo del TF
        }],
    )

    # ── 5. RPLIDAR A1M8 ─────────────────────────────────────────────────
    rplidar_node = Node(
        package='rplidar_ros',
        executable='rplidar_composition',
        name='rplidar_node',
        output='screen',
        parameters=[{
            'serial_port':      LaunchConfiguration('lidar_port'),
            'serial_baudrate':  115200,
            'frame_id':         'laser_frame',
            'angle_compensate': True,
            'scan_mode':        'Standard',
        }],
    )

    # ── 6. robot_localization EKF ────────────────────────────────────────
    # Fusiona /odom (wheel odometry) y publica:
    #   • /odometry/filtered  — odometría suavizada
    #   • TF odom → base_footprint  (publish_tf: true en ekf.yaml)
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config],
        remappings=[('odometry/filtered', '/odometry/filtered')],
    )

    # ── 7. safety_stop ──────────────────────────────────────────────────
    # Intercepta /cmd_vel_in y bloquea avance frontal si hay obstáculo
    # en el cono ±30°. Republica a /cmd_vel_safe.
    safety_stop = Node(
        package='rosmaster_hardware',
        executable='safety_stop.py',
        name='safety_stop',
        output='screen',
        parameters=[{
            'safety_distance':    0.3,
            'front_angle_window': 60.0,
            'enable':             True,
        }],
    )

    # ── 8. heading_controller ────────────────────────────────────────────
    # Corrige deriva angular en traslación pura. Escucha /cmd_vel_safe y
    # publica a /cmd_vel. La cadena completa:
    #   /cmd_vel_in → safety_stop → /cmd_vel_safe → heading_controller → /cmd_vel
    heading_controller = Node(
        package='rosmaster_hardware',
        executable='heading_controller.py',
        name='heading_controller',
        output='screen',
        parameters=[{
                'kp':                     1.0,
                'ki':                     0.2,
                'kd':                     0.5,
                'enable':                 True,
                'max_angular_correction': 1.0,
                'deadband':               0.05,
        }],
    )

    # ── 9. slam_toolbox (online_sync) ────────────────────────────────────
    # Usa /scan + TF (map→odom→base_footprint→laser_frame) y publica:
    #   • TF map → odom
    #   • /map  (OccupancyGrid)
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='sync_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            mapper_config,
            {'use_sim_time': False},
        ],
    )

    # ── Orden de arranque ────────────────────────────────────────────────
    # RSP + JSP arrancan primero (TF estático disponible de inmediato).
    # Hardware + SLAM arrancan 1s después para dar tiempo al URDF.
    delayed_stack = TimerAction(
        period=1.0,
        actions=[
            yahboom_driver,
            rosmaster_odom,
            rplidar_node,
            ekf_node,
            safety_stop,
            heading_controller,
        ],
    )
    # slam_toolbox necesita que el LiDAR ya esté publicando y el TF esté listo
    delayed_slam = TimerAction(
        period=3.0,
        actions=[slam_toolbox_node],
    )

    # ── nav2_lifecycle_manager: gestiona el ciclo de vida de slam_toolbox ──
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_slam',
        output='screen',
        parameters=[{
            'node_names': ['slam_toolbox'],
            'use_sim_time': False,
            'autostart': True,
        }],
    )

    return LaunchDescription([
        port_arg,
        lidar_port_arg,
        robot_state_publisher,
        joint_state_publisher,
        delayed_stack,
        delayed_slam,
        lifecycle_manager,
    ])
