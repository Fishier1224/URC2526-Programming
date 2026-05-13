#!/usr/bin/env python3
"""
joystick_node.py
─────────────────
Reads a gamepad via ROS2 joy and:
  - Publishes Twist to /joy_cmd for serial_bridge_node (MANUAL driving)
  - Publishes mode switch to /drive_mode on button press

Button mapping (Xbox / generic gamepad):
  Left stick  → drive (ly=forward, lx=turn)
  Start btn   → switch to AUTO mode
  Back btn    → switch to MANUAL mode

Install joy driver:
  sudo apt install ros-humble-joy
  ros2 run joy joy_node   (launched automatically by rover.launch.py)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from std_msgs.msg import String


# ── Button / axis indices (Xbox controller defaults) ──────────
AXIS_LEFT_LR  = 0   # left stick left/right  → lx (turning)
AXIS_LEFT_UD  = 1   # left stick up/down     → ly (forward)
BTN_START     = 7   # Start → switch to AUTO
BTN_BACK      = 6   # Back  → switch to MANUAL


class JoystickNode(Node):
    def __init__(self):
        super().__init__('joystick_node')

        self.declare_parameter('deadzone', 0.05)
        self.deadzone = self.get_parameter('deadzone').value

        self.cmd_pub  = self.create_publisher(Twist,  '/joy_cmd',    10)
        self.mode_pub = self.create_publisher(String, '/drive_mode', 10)

        self.create_subscription(Joy, '/joy', self.joy_cb, 10)

        self._last_start = 0
        self._last_back  = 0

        self.get_logger().info('joystick_node ready')

    def _apply_deadzone(self, val: float) -> float:
        return 0.0 if abs(val) < self.deadzone else val

    def joy_cb(self, msg: Joy):
        # ── Mode switching (rising edge on buttons) ──────────
        start = msg.buttons[BTN_START] if len(msg.buttons) > BTN_START else 0
        back  = msg.buttons[BTN_BACK]  if len(msg.buttons) > BTN_BACK  else 0

        if start and not self._last_start:
            mode_msg = String()
            mode_msg.data = 'AUTO'
            self.mode_pub.publish(mode_msg)
            self.get_logger().info('Switching to AUTO mode')

        if back and not self._last_back:
            mode_msg = String()
            mode_msg.data = 'MANUAL'
            self.mode_pub.publish(mode_msg)
            self.get_logger().info('Switching to MANUAL mode')

        self._last_start = start
        self._last_back  = back

        # ── Drive command ─────────────────────────────────────
        lx = self._apply_deadzone(
            msg.axes[AXIS_LEFT_LR]) if len(msg.axes) > AXIS_LEFT_LR else 0.0
        ly = self._apply_deadzone(
            msg.axes[AXIS_LEFT_UD]) if len(msg.axes) > AXIS_LEFT_UD else 0.0

        twist = Twist()
        twist.linear.x  = float(ly)   # forward/back
        twist.angular.z = float(lx)   # left/right turn
        self.cmd_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = JoystickNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
