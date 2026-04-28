from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='rosmaster_webrtc',
            executable='webrtc_bridge',
            name='mjpeg_bridge',
            parameters=[{
                'video_device':  1,
                'video_width':   320,
                'video_height':  240,
                'video_fps':     30,
                'jpeg_quality':  40,
                'http_port':     8080,
            }],
            output='screen',
        )
    ])
