"""
description_only.launch.py

Levanta únicamente robot_state_publisher y joint_state_publisher.
Útil para publicar el robot_description y /joint_states sin simulación ni RViz.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    pkg_description = get_package_share_directory('rosmaster_description')

    use_sim_arg = DeclareLaunchArgument(
        'use_sim',
        default_value='true',
        description='Selecciona el plugin de hardware: true=Gazebo, false=real'
    )

    xacro_file = os.path.join(pkg_description, 'urdf', 'rosmaster_x3.urdf.xacro')

    robot_description = {
        'robot_description': ParameterValue(
            Command(['xacro ', xacro_file, ' use_sim:=', LaunchConfiguration('use_sim')]),
            value_type=str
        )
    }

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
    )

    return LaunchDescription([
        use_sim_arg,
        robot_state_publisher,
        joint_state_publisher,
    ])
