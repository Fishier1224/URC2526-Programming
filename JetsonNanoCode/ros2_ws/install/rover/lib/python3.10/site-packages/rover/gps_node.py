#!/usr/bin/env python3
"""
gps_node.py
────────────
Wraps the adafruit_gps library and publishes to ROS2.

Publications:
    /gps/fix    sensor_msgs/NavSatFix   — position (consumed by robot_localization)

Install deps on Jetson:
    pip3 install adafruit-circuitpython-gps pyserial --break-system-packages
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, NavSatStatus

import serial
import adafruit_gps


class GpsNode(Node):
    def __init__(self):
        super().__init__('gps_node')

        self.declare_parameter('port',           '/dev/ttyUSB0')
        self.declare_parameter('baud',           9600)
        self.declare_parameter('update_rate_ms', 1000)   # 1 Hz default

        port    = self.get_parameter('port').value
        baud    = self.get_parameter('baud').value
        rate_ms = self.get_parameter('update_rate_ms').value

        # ── GPS hardware setup (Adafruit Ultimate GPS, UART) ──
        uart     = serial.Serial(port, baudrate=baud, timeout=1)
        self.gps = adafruit_gps.GPS(uart, debug=False)

        # GGA + RMC sentences only; disable the rest
        self.gps.send_command(
            b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0'
        )
        # Set update rate
        self.gps.send_command(f'PMTK220,{rate_ms}'.encode())

        # ── Publisher ─────────────────────────────────────────
        self.pub = self.create_publisher(NavSatFix, '/gps/fix', 10)

        # Poll at 2× the GPS update rate so we don't miss packets
        poll_hz = 2.0 / (rate_ms / 1000.0)
        self.create_timer(1.0 / poll_hz, self.update)

        self.get_logger().info(f'gps_node ready on {port}')

    def update(self):
        self.gps.update()

        if not self.gps.has_fix:
            self.get_logger().warn(
                'Waiting for GPS fix...', throttle_duration_sec=5.0
            )
            return

        msg = NavSatFix()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = 'gps_link'

        msg.latitude  = self.gps.latitude
        msg.longitude = self.gps.longitude
        msg.altitude  = self.gps.altitude_m if self.gps.altitude_m is not None else 0.0

        # Fix quality
        if self.gps.fix_quality == 0:
            msg.status.status = NavSatStatus.STATUS_NO_FIX
        elif self.gps.fix_quality >= 2:
            msg.status.status = NavSatStatus.STATUS_SBAS_FIX   # DGPS
        else:
            msg.status.status = NavSatStatus.STATUS_FIX

        msg.status.service = NavSatStatus.SERVICE_GPS

        # Position covariance — use HDOP if available
        if self.gps.horizontal_dilution is not None:
            sigma = self.gps.horizontal_dilution * 2.5   # rough: 1σ ≈ hdop * 2.5m
            cov   = sigma ** 2
        else:
            cov = 9.0   # default ~3 m sigma

        msg.position_covariance = [
            cov,  0.0,  0.0,
            0.0,  cov,  0.0,
            0.0,  0.0,  cov * 4,   # vertical is worse
        ]
        msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_APPROXIMATED

        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = GpsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
