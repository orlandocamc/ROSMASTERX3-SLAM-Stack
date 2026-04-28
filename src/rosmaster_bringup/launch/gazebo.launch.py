"""
gazebo.launch.py

Lanza la simulación completa del ROSMASTER X3 en Gazebo Harmonic.

Arquitectura de tópicos:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Gazebo Harmonic (gz sim)                                       │
  │    - Fisica + colisiones                                        │
  │    - Sensor gpu_lidar -> publica /scan en Gz internal           │
  │    - gz_ros2_control plugin -> expone hardware a ROS2           │
  └──────────────┬──────────────────────────────────────────────────┘
                 │ ros_gz_bridge (solo topics nativos de Gz)
  ┌──────────────▼──────────────────────────────────────────────────┐
  │  ROS2 (este proceso)                                            │
  │    robot_state_publisher  -> /robot_description, /tf, /tf_static│
  │    joint_state_broadcaster -> /joint_states                     │
  │    mecanum_drive_controller -> /odom, odom->base_footprint TF   │
  │    ros_gz_bridge          -> /clock, /scan, /cmd_vel            │
  └─────────────────────────────────────────────────────────────────┘

Topics que NO necesitan bridge (nativos de ROS2 via gz_ros2_control):
  /tf, /tf_static, /joint_states, /odom, /robot_description

Topics que SI necesitan bridge desde Gz:
  /clock  (Gz->ROS2)
  /scan   (Gz->ROS2)
  /cmd_vel (bidireccional)

Uso:
  ros2 launch rosmaster_bringup gazebo.launch.py           # headless (default)
  ros2 launch rosmaster_bringup gazebo.launch.py gui:=true # con ventana Gazebo
"""

import os

# ======================================================================
# Variables de entorno - configuradas a nivel modulo Python para que
# esten activas antes de que generate_launch_description() sea llamado.
#
# PLUGIN PATH: gz_sim.launch.py lee os.environ en su OpaqueFunction.
#   Si lo forzamos aqui, lo recoge aunque ROS no haya sido sourced.
#
# SOFTWARE RENDERING: RPi5 no soporta OpenGL 3.3 nativo.
#   LIBGL_ALWAYS_SOFTWARE=1  -> fuerza Mesa llvmpipe (CPU rendering)
#   MESA_GL_VERSION_OVERRIDE=3.3 -> reporta OpenGL 3.3 aunque sea sw
#   Esto permite que Gazebo arranque en RPi5 sin GPU dedicada.
# ======================================================================
_ROS_LIB = '/opt/ros/jazzy/lib'

# Plugin path para gz_ros2_control
_current_gz_plugin_path = os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', '')
if _ROS_LIB not in _current_gz_plugin_path.split(os.pathsep):
    os.environ['GZ_SIM_SYSTEM_PLUGIN_PATH'] = os.pathsep.join(
        filter(None, [_ROS_LIB, _current_gz_plugin_path])
    )

_current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
if _ROS_LIB not in _current_ld_path.split(os.pathsep):
    os.environ['LD_LIBRARY_PATH'] = os.pathsep.join(
        filter(None, [_ROS_LIB, _current_ld_path])
    )

# Software rendering para RPi5 (sin OpenGL 3.3 nativo)
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
os.environ['MESA_GL_VERSION_OVERRIDE'] = '3.3'

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    pkg_bringup     = get_package_share_directory('rosmaster_bringup')
    pkg_description = get_package_share_directory('rosmaster_description')
    pkg_ros_gz_sim  = get_package_share_directory('ros_gz_sim')

    world_file    = os.path.join(pkg_bringup, 'gazebo', 'worlds', 'empty_world.sdf')
    gz_sim_launch = os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')

    # ------------------------------------------------------------------ #
    # Acciones SetEnvironmentVariable (doble seguro sobre el nivel modulo)#
    # ------------------------------------------------------------------ #
    set_gz_plugin_path = SetEnvironmentVariable(
        name='GZ_SIM_SYSTEM_PLUGIN_PATH',
        value=os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', '')
    )
    set_libgl_software = SetEnvironmentVariable(
        name='LIBGL_ALWAYS_SOFTWARE', value='1'
    )
    set_mesa_gl_version = SetEnvironmentVariable(
        name='MESA_GL_VERSION_OVERRIDE', value='3.3'
    )

    # ------------------------------------------------------------------ #
    # Argumentos                                                           #
    # ------------------------------------------------------------------ #
    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='false',
        description=(
            'Abrir la ventana de Gazebo (true) o correr en modo headless (false). '
            'En false se usa -s --headless-rendering para mantener el rendering '
            'GPU necesario para el sensor gpu_lidar del RPLIDAR A1.'
        )
    )

    # ------------------------------------------------------------------ #
    # Robot description                                                    #
    # ------------------------------------------------------------------ #
    xacro_file = os.path.join(pkg_description, 'urdf', 'rosmaster_x3.urdf.xacro')

    robot_description = {
        'robot_description': ParameterValue(
            Command(['xacro ', xacro_file, ' use_sim:=true']),
            value_type=str
        )
    }

    # ------------------------------------------------------------------ #
    # Gazebo Harmonic - modo con GUI                                       #
    #   -r  : arrancar simulacion inmediatamente                           #
    #   -v4 : verbosidad nivel 4                                           #
    # ------------------------------------------------------------------ #
    gz_sim_with_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch),
        launch_arguments={
            'gz_args': f'-r -v4 {world_file}',
        }.items(),
        condition=IfCondition(LaunchConfiguration('gui')),
    )

    # ------------------------------------------------------------------ #
    # Gazebo Harmonic - modo headless (sin pantalla)                       #
    #   -s : solo servidor, sin ventana GUI                                #
    #   --headless-rendering NO se usa: requiere EGL/OpenGL nativo        #
    #   En su lugar se usa software rendering via llvmpipe                 #
    #   (LIBGL_ALWAYS_SOFTWARE=1 + MESA_GL_VERSION_OVERRIDE=3.3)          #
    #   El sensor lidar es CPU-based (type="lidar"), no necesita GPU.     #
    # ------------------------------------------------------------------ #
    gz_sim_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch),
        launch_arguments={
            'gz_args': f'-r -s -v4 {world_file}',
        }.items(),
        condition=UnlessCondition(LaunchConfiguration('gui')),
    )

    # ------------------------------------------------------------------ #
    # Robot State Publisher                                                #
    # Publica: /robot_description, /tf, /tf_static                        #
    # ------------------------------------------------------------------ #
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    )

    # ------------------------------------------------------------------ #
    # Spawn robot en Gazebo                                                #
    # El URDF contiene <gazebo><plugin filename="gz_ros2_control-system"  #
    # ...> que Gazebo carga al hacer spawn, iniciando controller_manager  #
    # ------------------------------------------------------------------ #
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_rosmaster_x3',
        arguments=[
            '-name',  'rosmaster_x3',
            '-topic', 'robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.05',
            '-R', '0.0',
            '-P', '0.0',
            '-Y', '0.0',
        ],
        output='screen',
    )

    # ------------------------------------------------------------------ #
    # ros_gz_bridge                                                        #
    #                                                                      #
    # Operadores de direccion:                                             #
    #   [gz_type  -> Gz->ROS2 (Gz publica, ROS2 suscribe)                #
    #   ]gz_type  -> ROS2->Gz (ROS2 publica, Gz suscribe)                #
    #   @gz_type  -> bidireccional                                         #
    #                                                                      #
    # Topics bridgeados desde Gz (nativos de Gazebo):                     #
    #   /clock  - reloj de simulacion                                      #
    #   /scan   - datos del sensor gpu_lidar (RPLIDAR A1 simulado)        #
    #   /cmd_vel - bidireccional para compatibilidad                       #
    #                                                                      #
    # NO se bridgean (ya son ROS2 nativos via gz_ros2_control):           #
    #   /tf, /tf_static   <- robot_state_publisher + mecanum_controller   #
    #   /joint_states     <- joint_state_broadcaster                      #
    #   /odom             <- mecanum_drive_controller                     #
    #   /robot_description<- robot_state_publisher                        #
    # ------------------------------------------------------------------ #
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
        ],
        output='screen',
    )

    # ------------------------------------------------------------------ #
    # Carga de controladores                                               #
    #                                                                      #
    # TimerAction en lugar de OnProcessExit(spawn_robot):                 #
    #   - spawn_robot termina inmediatamente tras enviar el modelo a Gz   #
    #   - gz_ros2_control necesita tiempo para inicializar el HW iface    #
    #   - En Raspberry Pi 5 el arranque es mas lento que en desktop       #
    #                                                                      #
    # Timer de 8 s para dar tiempo suficiente en RPi5.                    #
    # Secuencia:                                                           #
    #   t=0s -> arrancan Gazebo + RSP + spawn + bridge                    #
    #   t=8s -> cargar joint_state_broadcaster                            #
    #   JSB listo -> cargar mecanum_drive_controller                      #
    # ------------------------------------------------------------------ #
    load_joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen',
    )

    load_mecanum_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['mecanum_drive_controller'],
        output='screen',
    )

    delayed_load_jsb = TimerAction(
        period=8.0,
        actions=[load_joint_state_broadcaster],
    )

    load_mecanum_after_jsb = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[load_mecanum_controller],
        )
    )

    # ------------------------------------------------------------------ #
    # Relay: /mecanum_drive_controller/odometry -> /odom                  #
    #                                                                      #
    # El controlador corre dentro del proceso controller_manager, por lo  #
    # que los remappings del Node spawner no afectan sus topics.          #
    # Se usa un nodo relay externo que reenvía los mensajes al topic      #
    # estándar /odom que esperan nav2 y rviz2.                            #
    #                                                                      #
    # El TF odom->base_footprint se publica directamente en /tf por el   #
    # controlador gracias a enable_odom_tf: true en su configuración.    #
    #                                                                      #
    # Timer de 12 s para asegurar que el controlador ya esté activo      #
    # antes de que el relay intente suscribirse.                           #
    # ------------------------------------------------------------------ #
    odom_relay = Node(
        package='topic_tools',
        executable='relay',
        name='odom_relay',
        arguments=[
            '/mecanum_drive_controller/odometry',
            '/odom',
        ],
        output='screen',
    )

    tf_odom_relay = Node(
        package='topic_tools',
        executable='relay',
        name='tf_odom_relay',
        arguments=[
            '/mecanum_drive_controller/tf_odometry',
            '/tf',
        ],
        output='screen',
    )

    # ------------------------------------------------------------------ #
    # Twist → TwistStamped                                                 #
    #                                                                      #
    # mecanum_drive_controller en Jazzy escucha TwistStamped en           #
    # /mecanum_drive_controller/reference, no Twist en /cmd_vel.          #
    # Este nodo convierte y añade header.stamp + frame_id.                #
    # ------------------------------------------------------------------ #
    twist_stamper = Node(
        package='rosmaster_bringup',
        executable='twist_stamper.py',
        name='twist_stamper',
        output='screen',
    )

    delayed_odom_relay = TimerAction(
        period=12.0,
        actions=[odom_relay, tf_odom_relay, twist_stamper],
    )

    return LaunchDescription([
        # Env vars primero para que esten disponibles cuando gz sim arranca
        set_gz_plugin_path,
        set_libgl_software,
        set_mesa_gl_version,
        gui_arg,
        gz_sim_with_gui,
        gz_sim_headless,
        robot_state_publisher,
        spawn_robot,
        ros_gz_bridge,
        delayed_load_jsb,
        load_mecanum_after_jsb,
        delayed_odom_relay,
    ])
