#!/usr/bin/env python3
"""
rover.launch.py
────────────────
Launches the full rover stack:

  - gps_node                  adafruit GPS → /gps/fix
  - wheel_odom_node           VESC tachometer → /wheel_odom   (NEW)
  - Point-LIO                 LiDAR+IMU → /Odometry
  - robot_localization EKF    fused pose → /odometry/filtered
  - navsat_transform          GPS lat/lon → map frame
  - Nav2                      planning + obstacle avoidance
  - serial_bridge_node        Jetson ↔ Arduino (also publishes /arduino_raw)
  - joystick_node             gamepad input + mode switching
  - joy_node                  ROS2 gamepad driver
  - mission_node              waypoint execution + AR tag search

Pre-requisites (launch separately before this file):
  Unitree L2 LiDAR SDK node (headless, no RViz):
    ros2 launch unitree_lidar_ros2 lidar.launch.py

  The L2 connects over Ethernet (static IP 192.168.1.x).
  Verify your Jetson Ethernet interface has an IP in that subnet.

Usage:
  ros2 launch rover rover.launch.py
  ros2 launch rover rover.launch.py gps_port:=/dev/ttyUSB1 arduino_port:=/dev/ttyACM0
"""

import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def get_config(filename: str) -> str:
    share = get_package_share_directory('rover')
    return os.path.join(share, 'config', filename)


def generate_launch_description():

    # ── Launch arguments ─────────────────────────────────────
    gps_port_arg = DeclareLaunchArgument(
        'gps_port', default_value='/dev/ttyUSB0',
        description='Serial port for Adafruit Ultimate GPS')

    arduino_port_arg = DeclareLaunchArgument(
        'arduino_port', default_value='/dev/ttyACM0',
        description='USB serial port for Arduino Mega')

    gps_port     = LaunchConfiguration('gps_port')
    arduino_port = LaunchConfiguration('arduino_port')

    # ── GPS node ─────────────────────────────────────────────
    gps_node = Node(
        package='rover',
        executable='gps_node',
        name='gps_node',
        parameters=[{
            'port':           gps_port,
            'baud':           9600,
            'update_rate_ms': 1000,
        }],
        output='screen',
    )

    # ── Serial bridge (USB ↔ Arduino Mega) ───────────────────
    # Also publishes /arduino_raw for wheel_odom_node
    serial_bridge = Node(
        package='rover',
        executable='serial_bridge_node',
        name='serial_bridge_node',
        parameters=[{
            'port': arduino_port,
            'baud': 115200,
            'mode': 'MANUAL',   # always start in MANUAL for safety
        }],
        output='screen',
    )

    # ── Wheel odometry (VESC tachometer) ─────────────────────
    # Reads /arduino_raw, publishes /wheel_odom
    # !! TUNE pole_pairs and wheel_circ to match your motor + wheels !!
    wheel_odom_node = Node(
        package='rover',
        executable='wheel_odom_node',
        name='wheel_odom_node',
        parameters=[{
            'pole_pairs': 7,        # !! motor pole pairs — check motor spec !!
            'wheel_circ': 0.565,    # !! pi * wheel diameter in metres !!
            'wheel_base': 0.5,      # !! lateral distance between wheels in metres !!
        }],
        output='screen',
    )

    # ── Point-LIO (LiDAR + IMU odometry) ────────────────────
    # Reads:  /unilidar/cloud  +  /unilidar/imu
    # Writes: /Odometry  (capital O)
    #
    # Keep rover stationary for ~3 seconds on startup so
    # Point-LIO can initialise IMU bias correctly.
    point_lio_node = Node(
        package='point_lio',
        executable='pointlio_mapping',
        name='point_lio',
        parameters=[get_config('point_lio_l2.yaml')],
        output='screen',
    )

    # ── robot_localization EKF ───────────────────────────────
    # Fuses /Odometry + /wheel_odom + /odometry/gps → /odometry/filtered
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        parameters=[get_config('ekf.yaml')],
        output='screen',
    )

    # ── navsat_transform ─────────────────────────────────────
    # Converts /gps/fix (lat/lon) → /odometry/gps (XY in odom frame)
    navsat_node = Node(
        package='robot_localization',
        executable='navsat_transform_node',
        name='navsat_transform',
        parameters=[get_config('ekf.yaml')],
        remappings=[
            ('/gps/fix',           '/gps/fix'),
            ('/odometry/filtered', '/odometry/filtered'),
            ('/odometry/gps',      '/odometry/gps'),
        ],
        output='screen',
    )

    # ── Nav2 ─────────────────────────────────────────────────
    nav2_bringup_share = get_package_share_directory('nav2_bringup')
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_share, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'params_file':   get_config('nav2_params.yaml'),
            'use_sim_time':  'false',
        }.items(),
    )

    # ── ROS2 joy driver (gamepad) ─────────────────────────────
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[{
            'device_id':       0,
            'deadzone':        0.05,
            'autorepeat_rate': 20.0,
        }],
        output='screen',
    )

    # ── Joystick node (ROS joy → /joy_cmd + mode switch) ─────
    joystick = Node(
        package='rover',
        executable='joystick_node',
        name='joystick_node',
        output='screen',
    )

    # ── Mission node ─────────────────────────────────────────
    mission = Node(
        package='rover',
        executable='mission_node',
        name='mission_node',
        parameters=[{
            'search_box_size': 10.0,
            'search_spacing':   2.0,
        }],
        output='screen',
    )

    return LaunchDescription([
        # Args
        gps_port_arg,
        arduino_port_arg,
        # Hardware interfaces
        gps_node,
        serial_bridge,
        wheel_odom_node,
        # LiDAR odometry
        point_lio_node,
        # Localisation
        ekf_node,
        navsat_node,
        # Navigation
        nav2_launch,
        # Teleop
        joy_node,
        joystick,
        # Mission
        mission,
    ])
