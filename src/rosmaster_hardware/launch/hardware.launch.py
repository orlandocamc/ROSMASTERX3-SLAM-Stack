"""
hardware.launch.py

Lanza el driver serial Yahboom para el ROSMASTER X3 en hardware real.

Uso:
  ros2 launch rosmaster_hardware hardware.launch.py
  ros2 launch rosmaster_hardware hardware.launch.py port:=/dev/ttyUSB1
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    port_arg = DeclareLaunchArgument(
        'port',
        default_value='/dev/yahboom',
        description='Puerto serial del STM32 Yahboom (chip CH340)',
    )

    baudrate_arg = DeclareLaunchArgument(
        'baudrate',
        default_value='115200',
        description='Velocidad del puerto serial',
    )

    tx_cmd_id_arg = DeclareLaunchArgument(
        'tx_cmd_id',
        default_value='1',
        description='CMD ID del paquete TX (1=0x01 default, 2=0x02 alternativo)',
    )

    yahboom_driver = Node(
        package='rosmaster_hardware',
        executable='yahboom_driver.py',
        name='yahboom_driver',
        output='screen',
        parameters=[{
            'port':       LaunchConfiguration('port'),
            'baudrate':   LaunchConfiguration('baudrate'),
            'tx_cmd_id':  LaunchConfiguration('tx_cmd_id'),
        }],
    )

    return LaunchDescription([
        port_arg,
        baudrate_arg,
        tx_cmd_id_arg,
        yahboom_driver,
    ])
