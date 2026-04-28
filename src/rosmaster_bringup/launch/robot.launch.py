"""
robot.launch.py

Stack de hardware real para el ROSMASTER X3:
  1. robot_state_publisher  — TF tree del robot (use_sim:=false)
  2. joint_state_publisher  — estados de articulaciones para RViz
  3. yahboom_driver          — driver STM32 vía Rosmaster_Lib (/dev/yahboom)
  4. rosmaster_odom          — odometría integrada + TF odom→base_footprint
  5. rplidar_node            — RPLIDAR A1M8 (/dev/rplidar)
  6. twist_stamper           — Twist → TwistStamped (compatibilidad teleop)

Puertos fijos via udev (99-rosmaster.rules):
  /dev/yahboom  →  CH340  (1a86:7523)  STM32 Yahboom
  /dev/rplidar  →  CP2102 (10c4:ea60)  RPLIDAR A1M8
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

    # ------------------------------------------------------------------ #
    # Arguments                                                            #
    # ------------------------------------------------------------------ #
    port_arg = DeclareLaunchArgument(
        'port',
        default_value='/dev/yahboom',
        description='Puerto serial STM32 Yahboom (udev: /dev/yahboom)'
    )

    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port',
        default_value='/dev/rplidar',
        description='Puerto serial RPLIDAR A1M8 (udev: /dev/rplidar)'
    )

    # ------------------------------------------------------------------ #
    # 1. robot_state_publisher (use_sim:=false)                           #
    # ------------------------------------------------------------------ #
    xacro_file = os.path.join(pkg_description, 'urdf', 'rosmaster_x3.urdf.xacro')

    robot_description_content = ParameterValue(
        Command(['xacro ', xacro_file, ' use_sim:=false']),
        value_type=str
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_content}],
    )

    # ------------------------------------------------------------------ #
    # 2. joint_state_publisher (visualización de ruedas en RViz)          #
    # ------------------------------------------------------------------ #
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
    )

    # ------------------------------------------------------------------ #
    # 3. yahboom_driver (Rosmaster_Lib)                                   #
    # ------------------------------------------------------------------ #
    yahboom_driver = Node(
        package='rosmaster_hardware',
        executable='yahboom_driver.py',
        name='yahboom_driver',
        output='screen',
        parameters=[{'port': LaunchConfiguration('port')}],
    )

    # ------------------------------------------------------------------ #
    # 4. rosmaster_odom — odometría integrada + TF odom→base_footprint    #
    # ------------------------------------------------------------------ #
    rosmaster_odom = Node(
        package='rosmaster_hardware',
        executable='rosmaster_odom.py',
        name='rosmaster_odom',
        output='screen',
        parameters=[{'port': LaunchConfiguration('port')}],
    )

    # ------------------------------------------------------------------ #
    # 5. RPLIDAR A1M8                                                      #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # 6. twist_stamper (Twist → TwistStamped para compatibilidad teleop)  #
    # ------------------------------------------------------------------ #
    twist_stamper = Node(
        package='rosmaster_bringup',
        executable='twist_stamper.py',
        name='twist_stamper',
        output='screen',
    )

    # ------------------------------------------------------------------ #
    # Orden de arranque: RSP + JSP → stack hardware (1 s delay)          #
    # ------------------------------------------------------------------ #
    delayed_stack = TimerAction(
        period=1.0,
        actions=[yahboom_driver, rosmaster_odom, rplidar_node, twist_stamper],
    )

    return LaunchDescription([
        port_arg,
        lidar_port_arg,
        robot_state_publisher,
        joint_state_publisher,
        delayed_stack,
    ])
