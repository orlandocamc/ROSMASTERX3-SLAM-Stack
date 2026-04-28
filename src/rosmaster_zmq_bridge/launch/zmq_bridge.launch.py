import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_prefix


def generate_launch_description():
    pkg_lib = os.path.join(
        get_package_prefix('rosmaster_zmq_bridge'),
        'lib', 'rosmaster_zmq_bridge'
    )
    flask_script = os.path.join(pkg_lib, 'flask_teleop_server.py')

    video_device_arg = DeclareLaunchArgument(
        'video_device',
        default_value='0',
        description='Índice del dispositivo V4L2 (e.g. 0 para /dev/video0)',
    )

    return LaunchDescription([
        video_device_arg,
        Node(
            package='rosmaster_zmq_bridge',
            executable='zmq_video_publisher.py',
            name='zmq_video_publisher',
            output='screen',
            parameters=[{'video_device': LaunchConfiguration('video_device')}],
        ),
        Node(
            package='rosmaster_zmq_bridge',
            executable='zmq_sensors_publisher.py',
            name='zmq_sensors_publisher',
            output='screen',
        ),
        Node(
            package='rosmaster_zmq_bridge',
            executable='zmq_cmd_subscriber.py',
            name='zmq_cmd_subscriber',
            output='screen',
        ),
        ExecuteProcess(
            cmd=['python3', flask_script],
            output='screen',
        ),
    ])
