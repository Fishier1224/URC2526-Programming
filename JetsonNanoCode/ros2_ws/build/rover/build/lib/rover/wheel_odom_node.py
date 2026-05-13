#!/usr/bin/env python3
"""
wheel_odom_node.py
───────────────────
Reads VESC tachometer + RPM from the Arduino serial bridge and
publishes a nav_msgs/Odometry on /wheel_odom.

The EKF in ekf.yaml can fuse this alongside Point-LIO odometry
as an optional second odometry source (useful if LiDAR drops out).

Serial packet from Arduino (sent at 20 Hz):
    <ODOM,ticksL,ticksR,rpmL,rpmR>

VESC tachometer tick → metres conversion:
    metres = ticks / (POLE_PAIRS * 6) * WHEEL_CIRCUMFERENCE

Published topics:
    /wheel_odom          nav_msgs/Odometry   — wheel dead-reckoning pose + twist
    /wheel_odom/ticks    std_msgs/String      — raw tick string (debug)

Parameters:
    port                 str     /dev/ttyACM0   — same USB serial as serial_bridge_node
                                                   (this node subscribes to the parsed
                                                   packets via serial_bridge_node's
                                                   /arduino_raw topic instead of opening
                                                   the port itself — see note below)

NOTE ON SERIAL SHARING:
    Two nodes cannot both open the same serial port. This node subscribes to
    /arduino_raw (std_msgs/String) which serial_bridge_node publishes for every
    line received from the Arduino. No second serial port needed.

    Make sure serial_bridge_node publishes /arduino_raw — the updated version
    in this package does so automatically.
"""

import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros


class WheelOdomNode(Node):
    def __init__(self):
        super().__init__('wheel_odom_node')

        # ── Physical parameters ────────────────────────────────
        # TUNE THESE to match your rover:
        self.declare_parameter('pole_pairs',       7)      # motor pole pairs
        self.declare_parameter('wheel_circ',       0.565)  # metres (pi * diameter)
        self.declare_parameter('wheel_base',       0.5)    # metres (lateral centre-to-centre)
        self.declare_parameter('ticks_per_rev_override', -1)  # set if you know exact value

        self.pole_pairs  = self.get_parameter('pole_pairs').value
        self.wheel_circ  = self.get_parameter('wheel_circ').value
        self.wheel_base  = self.get_parameter('wheel_base').value

        override = self.get_parameter('ticks_per_rev_override').value
        self.ticks_per_rev = override if override > 0 else self.pole_pairs * 6

        self.get_logger().info(
            f'Wheel odom: pole_pairs={self.pole_pairs}, '
            f'ticks_per_rev={self.ticks_per_rev}, '
            f'wheel_circ={self.wheel_circ:.3f}m, '
            f'wheel_base={self.wheel_base:.3f}m'
        )

        # ── State ──────────────────────────────────────────────
        self.prev_ticks_l: int | None = None
        self.prev_ticks_r: int | None = None
        self.prev_time = None

        # Integrated pose
        self.x   = 0.0
        self.y   = 0.0
        self.yaw = 0.0

        # ── Publishers ─────────────────────────────────────────
        self.odom_pub  = self.create_publisher(Odometry, '/wheel_odom', 10)
        self.debug_pub = self.create_publisher(String,   '/wheel_odom/ticks', 10)

        # ── TF broadcaster ─────────────────────────────────────
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # ── Subscription — raw Arduino lines ───────────────────
        self.create_subscription(String, '/arduino_raw', self._raw_cb, 50)

        self.get_logger().info('wheel_odom_node ready — listening on /arduino_raw')

    # ── Helpers ────────────────────────────────────────────────

    def _ticks_to_metres(self, ticks: int) -> float:
        return (ticks / self.ticks_per_rev) * self.wheel_circ

    # ── Callback ───────────────────────────────────────────────

    def _raw_cb(self, msg: String):
        line = msg.data.strip()
        if not (line.startswith('<ODOM,') and line.endswith('>')):
            return

        # Debug publish
        dbg = String()
        dbg.data = line
        self.debug_pub.publish(dbg)

        # Parse <ODOM,ticksL,ticksR,rpmL,rpmR>
        inner = line[1:-1]          # strip < >
        parts = inner.split(',')    # ['ODOM', tL, tR, rpmL, rpmR]
        if len(parts) != 5:
            self.get_logger().warn(f'Bad ODOM packet: {line}', throttle_duration_sec=2.0)
            return

        try:
            ticks_l = int(parts[1])
            ticks_r = int(parts[2])
            rpm_l   = float(parts[3])
            rpm_r   = float(parts[4])
        except ValueError:
            self.get_logger().warn(f'ODOM parse error: {line}', throttle_duration_sec=2.0)
            return

        now = self.get_clock().now()

        # First packet — initialise reference ticks
        if self.prev_ticks_l is None:
            self.prev_ticks_l = ticks_l
            self.prev_ticks_r = ticks_r
            self.prev_time    = now
            return

        # ── Delta ticks → delta metres per wheel ──────────────
        d_ticks_l = ticks_l - self.prev_ticks_l
        d_ticks_r = ticks_r - self.prev_ticks_r

        # NOTE: VESC tachometerAbs is unsigned and cumulative; it resets to 0
        # on power cycle but does NOT overflow for normal mission lengths.
        # If your rover will run for many hours, add rollover handling here.

        d_left  = self._ticks_to_metres(d_ticks_l)
        d_right = self._ticks_to_metres(d_ticks_r)

        # ── dt ────────────────────────────────────────────────
        dt_ns = (now - self.prev_time).nanoseconds
        dt    = dt_ns * 1e-9
        if dt <= 0.0:
            return

        # ── Differential drive kinematics ─────────────────────
        d_centre = (d_left + d_right) / 2.0
        d_theta  = (d_right - d_left) / self.wheel_base

        # Integrate pose
        self.x   += d_centre * math.cos(self.yaw + d_theta / 2.0)
        self.y   += d_centre * math.sin(self.yaw + d_theta / 2.0)
        self.yaw += d_theta
        # Normalise yaw to (-pi, pi)
        self.yaw  = math.atan2(math.sin(self.yaw), math.cos(self.yaw))

        # ── Twist (velocities in base_link frame) ──────────────
        vx = d_centre / dt
        vth = d_theta  / dt

        # ── RPM → wheel velocities (for covariance / sanity) ──
        # rpm_l and rpm_r are from VESC data.rpm (electrical RPM)
        # Convert to linear wheel speed: v = (rpm / pole_pairs / 60) * wheel_circ
        v_l_rpm = (rpm_l / self.pole_pairs / 60.0) * self.wheel_circ
        v_r_rpm = (rpm_r / self.pole_pairs / 60.0) * self.wheel_circ
        vx_rpm  = (v_l_rpm + v_r_rpm) / 2.0  # cross-check against tick-based vx

        # ── Build Odometry message ─────────────────────────────
        odom = Odometry()
        odom.header.stamp    = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id  = 'base_link'

        # Pose
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0

        # Convert yaw → quaternion (z-axis rotation only)
        odom.pose.pose.orientation.z = math.sin(self.yaw / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.yaw / 2.0)

        # Pose covariance (row-major 6x6: x,y,z,roll,pitch,yaw)
        # Wheel odometry on desert terrain — generous uncertainty on x,y,yaw
        pose_cov = [0.0] * 36
        pose_cov[0]  = 0.1    # x
        pose_cov[7]  = 0.1    # y
        pose_cov[14] = 1e6    # z  — not sensed
        pose_cov[21] = 1e6    # roll
        pose_cov[28] = 1e6    # pitch
        pose_cov[35] = 0.2    # yaw — wheel slip adds uncertainty
        odom.pose.covariance = pose_cov

        # Twist
        odom.twist.twist.linear.x  = vx
        odom.twist.twist.angular.z = vth

        twist_cov = [0.0] * 36
        twist_cov[0]  = 0.05   # vx
        twist_cov[7]  = 1e6    # vy (non-holonomic — we don't slide sideways ideally)
        twist_cov[14] = 1e6    # vz
        twist_cov[21] = 1e6    # vroll
        twist_cov[28] = 1e6    # vpitch
        twist_cov[35] = 0.1    # vyaw
        odom.twist.covariance = twist_cov

        self.odom_pub.publish(odom)

        # ── TF: odom → base_link ───────────────────────────────
        tf = TransformStamped()
        tf.header.stamp    = now.to_msg()
        tf.header.frame_id = 'odom'
        tf.child_frame_id  = 'base_link'
        tf.transform.translation.x = self.x
        tf.transform.translation.y = self.y
        tf.transform.translation.z = 0.0
        tf.transform.rotation.z    = math.sin(self.yaw / 2.0)
        tf.transform.rotation.w    = math.cos(self.yaw / 2.0)
        self.tf_broadcaster.sendTransform(tf)

        # ── Update state ───────────────────────────────────────
        self.prev_ticks_l = ticks_l
        self.prev_ticks_r = ticks_r
        self.prev_time    = now

        self.get_logger().debug(
            f'odom x={self.x:.3f} y={self.y:.3f} yaw={math.degrees(self.yaw):.1f}° '
            f'vx={vx:.3f} vx_rpm={vx_rpm:.3f}',
        )


def main(args=None):
    rclpy.init(args=args)
    node = WheelOdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
