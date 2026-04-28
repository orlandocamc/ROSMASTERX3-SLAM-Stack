"""
description.launch.py

Launches robot_state_publisher with the ROSMASTER X3 URDF.
Can be included by other launch files.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    pkg_description = get_package_share_directory('rosmaster_description')

    # ------------------------------------------------------------------ #
    # Arguments                                                            #
    # ------------------------------------------------------------------ #
    use_sim_arg = DeclareLaunchArgument(
        'use_sim',
        default_value='true',
        description='Use simulation (Gazebo) hardware interfaces when true'
    )

    use_jsp_gui_arg = DeclareLaunchArgument(
        'use_jsp_gui',
        default_value='false',
        description='Start joint_state_publisher_gui instead of joint_state_publisher'
    )

    # ------------------------------------------------------------------ #
    # Robot description via xacro                                          #
    # ------------------------------------------------------------------ #
    xacro_file = os.path.join(pkg_description, 'urdf', 'rosmaster_x3.urdf.xacro')

    robot_description_content = ParameterValue(
        Command([
            'xacro ', xacro_file,
            ' use_sim:=', LaunchConfiguration('use_sim'),
        ]),
        value_type=str
    )

    robot_description = {'robot_description': robot_description_content}

    # ------------------------------------------------------------------ #
    # Nodes                                                                #
    # ------------------------------------------------------------------ #
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    )

    # joint_state_publisher (needed when no controllers publish joint states)
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        condition=None,  # always start; controllers will override in simulation
    )

    return LaunchDescription([
        use_sim_arg,
        use_jsp_gui_arg,
        robot_state_publisher_node,
        joint_state_publisher_node,
    ])
