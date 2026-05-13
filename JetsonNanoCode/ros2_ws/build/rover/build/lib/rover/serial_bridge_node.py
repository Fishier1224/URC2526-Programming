#!/usr/bin/env python3
"""
serial_bridge_node.py
─────────────────────
Bridges ROS2 ↔ Arduino Mega over USB serial.

Subscriptions:
    /cmd_vel          geometry_msgs/Twist   — from Nav2 (AUTO mode)
    /joy_cmd          geometry_msgs/Twist   — from joystick_node (MANUAL mode)
    /drive_mode       std_msgs/String       — "AUTO" or "MANUAL"

Publications:
    /drive_mode_ack   std_msgs/String       — echoes Arduino ACK
    /arduino_raw      std_msgs/String       — every raw line from Arduino
                                              (consumed by wheel_odom_node)

Parameters:
    port    str     /dev/ttyACM0   — USB serial to Arduino Mega
    baud    int     115200
    mode    str     MANUAL         — starting drive mode
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import serial
import threading


class SerialBridgeNode(Node):
    def __init__(self):
        super().__init__('serial_bridge_node')

        # ── Parameters ──────────────────────────────────────────
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('mode', 'MANUAL')

        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value
        self.mode = self.get_parameter('mode').value

        # ── Serial ──────────────────────────────────────────────
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.get_logger().info(f'Serial connected on {port} at {baud}')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open serial port: {e}')
            raise

        # ── Publishers ───────────────────────────────────────────
        self.ack_pub   = self.create_publisher(String, '/drive_mode_ack', 10)
        self.raw_pub   = self.create_publisher(String, '/arduino_raw',    50)

        # ── Subscriptions ────────────────────────────────────────
        self.create_subscription(Twist,  '/cmd_vel',    self.cmd_vel_cb, 10)
        self.create_subscription(Twist,  '/joy_cmd',    self.joy_cmd_cb, 10)
        self.create_subscription(String, '/drive_mode', self.mode_cb,    10)

        # ── Serial read thread ────────────────────────────────────
        self._read_thread = threading.Thread(target=self._read_serial, daemon=True)
        self._read_thread.start()

        self.get_logger().info(
            f'serial_bridge_node ready — starting in {self.mode} mode'
        )
        self._send_mode(self.mode)

    # ── Serial write helpers ─────────────────────────────────────

    def _send(self, packet: str):
        """Send a newline-terminated packet to the Arduino."""
        try:
            self.ser.write((packet + '\n').encode())
        except serial.SerialException as e:
            self.get_logger().error(f'Serial write error: {e}')

    def _send_mode(self, mode: str):
        self._send(f'<MODE,{mode}>')

    def _send_auto(self, linear: float, angular: float):
        self._send(f'<A,{linear:.4f},{angular:.4f}>')

    def _send_manual(self, lx: float, ly: float,
                     lb=0, lt=0, rb=0, rt=0):
        self._send(f'<M,{lx:.4f},{ly:.4f},{lb},{lt},{rb},{rt}>')

    # ── Callbacks ─────────────────────────────────────────────────

    def cmd_vel_cb(self, msg: Twist):
        """Nav2 velocity commands — only forwarded in AUTO mode."""
        if self.mode != 'AUTO':
            return
        self._send_auto(msg.linear.x, msg.angular.z)

    def joy_cmd_cb(self, msg: Twist):
        """Joystick commands — only forwarded in MANUAL mode."""
        if self.mode != 'MANUAL':
            return
        self._send_manual(msg.angular.z, msg.linear.x)

    def mode_cb(self, msg: String):
        """Switch drive mode."""
        new_mode = msg.data.upper()
        if new_mode not in ('AUTO', 'MANUAL'):
            self.get_logger().warn(f'Unknown mode: {new_mode}')
            return
        if new_mode == self.mode:
            return
        self.mode = new_mode
        self._send_mode(self.mode)
        self.get_logger().info(f'Mode switched to {self.mode}')

    # ── Serial read thread ────────────────────────────────────────

    def _read_serial(self):
        """
        Read lines from Arduino and republish.
        - <ODOM,...> lines go to /arduino_raw for wheel_odom_node
        - ACK:* lines go to /drive_mode_ack
        - Everything goes to /arduino_raw so any node can listen
        """
        while rclpy.ok():
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                self.get_logger().debug(f'Arduino: {line}')

                # Publish every line as raw
                raw_msg = String()
                raw_msg.data = line
                self.raw_pub.publish(raw_msg)

                # Also republish ACKs on their own topic
                if line.startswith('ACK:'):
                    ack_msg = String()
                    ack_msg.data = line
                    self.ack_pub.publish(ack_msg)

            except Exception as e:
                self.get_logger().warn(
                    f'Serial read error: {e}', throttle_duration_sec=5.0
                )


def main(args=None):
    rclpy.init(args=args)
    node = SerialBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
