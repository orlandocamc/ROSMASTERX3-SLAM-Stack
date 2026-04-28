"""
rviz.launch.py

Launches RViz2 with the ROSMASTER X3 configuration.
Optionally starts robot_state_publisher and joint_state_publisher
for standalone visualization (no Gazebo / real robot needed).
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    pkg_description = get_package_share_directory('rosmaster_description')
    pkg_bringup     = get_package_share_directory('rosmaster_bringup')

    rviz_config = os.path.join(pkg_bringup, 'rviz', 'rosmaster_x3.rviz')

    # ------------------------------------------------------------------ #
    # Arguments                                                            #
    # ------------------------------------------------------------------ #
    start_rsp_arg = DeclareLaunchArgument(
        'start_rsp',
        default_value='true',
        description='Start robot_state_publisher (set false if already running)'
    )

    start_jsp_arg = DeclareLaunchArgument(
        'start_jsp',
        default_value='true',
        description='Start joint_state_publisher (set false if controllers are active)'
    )

    use_jsp_gui_arg = DeclareLaunchArgument(
        'use_jsp_gui',
        default_value='false',
        description='Use joint_state_publisher_gui instead of joint_state_publisher'
    )

    # ------------------------------------------------------------------ #
    # Robot description                                                    #
    # ------------------------------------------------------------------ #
    xacro_file = os.path.join(pkg_description, 'urdf', 'rosmaster_x3.urdf.xacro')

    robot_description_content = ParameterValue(
        Command(['xacro ', xacro_file, ' use_sim:=true']),
        value_type=str
    )

    robot_description = {'robot_description': robot_description_content}

    # ------------------------------------------------------------------ #
    # Nodes                                                                #
    # ------------------------------------------------------------------ #
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
        condition=IfCondition(LaunchConfiguration('start_rsp')),
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        condition=IfCondition(LaunchConfiguration('start_jsp')),
    )

    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        condition=IfCondition(LaunchConfiguration('use_jsp_gui')),
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        output='screen',
    )

    return LaunchDescription([
        start_rsp_arg,
        start_jsp_arg,
        use_jsp_gui_arg,
        robot_state_publisher,
        joint_state_publisher,
        joint_state_publisher_gui,
        rviz2,
    ])
