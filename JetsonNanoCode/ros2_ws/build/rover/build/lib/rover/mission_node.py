#!/usr/bin/env python3
"""
mission_node.py
────────────────
Executes the 3-waypoint URC mission:

  1. Convert GNSS lat/lon waypoints → map frame goals
  2. Send goals one-by-one to Nav2 NavigateToPose
  3. On arrival, check stop condition:
       - Waypoints 1 & 2: stop within 3m of detected object
       - Waypoint 3 (AR tag search): run lawnmower search in 10x10m box,
         stop when AR tag detected
  4. After each waypoint is complete, proceed to next

Subscriptions:
    /target_detected   std_msgs/Bool   — object detection (your existing node)
    /ar_tag_detected   std_msgs/Bool   — AR tag detection  (your existing node)

Publications:
    /drive_mode        std_msgs/String — switches Arduino to AUTO/MANUAL

Parameters (set in launch file):
    waypoints:        list of [lat, lon] pairs   ← FILL THESE IN
    search_box_size:  float (metres)              default 10.0
    search_spacing:   float (metres)              default 2.0
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup

from std_msgs.msg import Bool, String
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose, NavigateThroughPoses

import math


# ══════════════════════════════════════════════════════════════
#  !! FILL IN YOUR WAYPOINTS BEFORE COMPETITION !!
#  Format: [latitude, longitude]
#  Waypoint 3 is the AR tag search area centre
# ══════════════════════════════════════════════════════════════
WAYPOINTS_LATLON = [
    [0.0, 0.0],   # Waypoint 1 — object detection stop
    [0.0, 0.0],   # Waypoint 2 — object detection stop
    [0.0, 0.0],   # Waypoint 3 — AR tag search
]


class MissionNode(Node):
    def __init__(self):
        super().__init__('mission_node')
        self.cb_group = ReentrantCallbackGroup()

        # ── Parameters ──────────────────────────────────────
        self.declare_parameter('search_box_size', 10.0)
        self.declare_parameter('search_spacing',   2.0)
        self.search_box     = self.get_parameter('search_box_size').value
        self.search_spacing = self.get_parameter('search_spacing').value

        # ── State ────────────────────────────────────────────
        self.object_detected  = False
        self.ar_tag_detected  = False
        self.current_waypoint = 0
        self._nav_goal_handle    = None
        self._search_goal_handle = None
        self._mission_started    = False
        self._waiting_for_nav    = False
        self._doing_search       = False

        # ── Publishers ───────────────────────────────────────
        self.mode_pub = self.create_publisher(String, '/drive_mode', 10)

        # ── Subscriptions ────────────────────────────────────
        self.create_subscription(
            Bool, '/target_detected', self._obj_cb, 10,
            callback_group=self.cb_group)
        self.create_subscription(
            Bool, '/ar_tag_detected', self._ar_cb, 10,
            callback_group=self.cb_group)

        # ── Nav2 action clients ──────────────────────────────
        self._nav_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose',
            callback_group=self.cb_group)
        self._through_client = ActionClient(
            self, NavigateThroughPoses, 'navigate_through_poses',
            callback_group=self.cb_group)

        # ── Wait for Nav2 then start ─────────────────────────
        self.get_logger().info('Waiting for Nav2 action server...')
        self._nav_client.wait_for_server()
        self.get_logger().info('Nav2 ready — starting mission')

        self._switch_mode('AUTO')
        self.create_timer(1.0, self._mission_tick, callback_group=self.cb_group)

    # ── Mode switch ──────────────────────────────────────────

    def _switch_mode(self, mode: str):
        msg = String()
        msg.data = mode
        self.mode_pub.publish(msg)

    # ── Detection callbacks ──────────────────────────────────

    def _obj_cb(self, msg: Bool):
        if msg.data and not self.object_detected:
            self.get_logger().info('Object detected — cancelling nav goal')
            self.object_detected = True
            self._cancel_current_goal()

    def _ar_cb(self, msg: Bool):
        if msg.data and not self.ar_tag_detected:
            self.get_logger().info('AR tag detected — cancelling search')
            self.ar_tag_detected = True
            self._cancel_current_goal()

    def _cancel_current_goal(self):
        if self._nav_goal_handle is not None:
            self._nav_goal_handle.cancel_goal_async()
            self._nav_goal_handle = None
        if self._search_goal_handle is not None:
            self._search_goal_handle.cancel_goal_async()
            self._search_goal_handle = None

    # ── Coordinate conversion ────────────────────────────────

    def _latlon_to_map(self, lat: float, lon: float) -> PoseStamped:
        """
        Flat-earth approximation: convert lat/lon to map frame XY
        relative to the first waypoint as the local origin.
        Accurate to centimetres for distances < 1 km.
        robot_localization's navsat_transform publishes the
        UTM→map transform at startup using the first GPS fix as datum.
        """
        origin_lat = WAYPOINTS_LATLON[0][0]
        origin_lon = WAYPOINTS_LATLON[0][1]

        x = (lon - origin_lon) * 111320.0 * math.cos(math.radians(origin_lat))
        y = (lat - origin_lat) * 111320.0

        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp    = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
        pose.pose.orientation.w = 1.0
        return pose

    # ── Navigation helpers ───────────────────────────────────

    def _send_nav_goal(self, pose: PoseStamped):
        goal = NavigateToPose.Goal()
        goal.pose = pose
        future = self._nav_client.send_goal_async(goal)
        future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn('Nav goal rejected')
            self._waiting_for_nav = False
            return
        self._nav_goal_handle = handle
        result_future = handle.get_result_async()
        result_future.add_done_callback(self._goal_result_cb)

    def _goal_result_cb(self, future):
        self._nav_goal_handle = None
        self._waiting_for_nav = False
        self.get_logger().info(
            f'Waypoint {self.current_waypoint} navigation complete'
        )

    # ── Lawnmower search ─────────────────────────────────────

    def _generate_lawnmower(self, centre_x: float, centre_y: float):
        half  = self.search_box / 2.0
        poses = []
        y     = centre_y - half
        direction = 1

        while y <= centre_y + half:
            x_start = centre_x - half if direction == 1 else centre_x + half
            x_end   = centre_x + half if direction == 1 else centre_x - half

            for x in [x_start, x_end]:
                pose = PoseStamped()
                pose.header.frame_id = 'map'
                pose.header.stamp    = self.get_clock().now().to_msg()
                pose.pose.position.x = x
                pose.pose.position.y = y
                pose.pose.position.z = 0.0
                pose.pose.orientation.w = 1.0
                poses.append(pose)

            y         += self.search_spacing
            direction *= -1

        return poses

    def _start_search(self, centre_pose: PoseStamped):
        self.get_logger().info('Starting lawnmower AR tag search...')
        poses = self._generate_lawnmower(
            centre_pose.pose.position.x,
            centre_pose.pose.position.y)

        goal       = NavigateThroughPoses.Goal()
        goal.poses = poses
        future     = self._through_client.send_goal_async(goal)
        future.add_done_callback(self._search_response_cb)

    def _search_response_cb(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn('Search goal rejected')
            self._doing_search = False
            return
        self._search_goal_handle = handle
        result_future = handle.get_result_async()
        result_future.add_done_callback(self._search_result_cb)

    def _search_result_cb(self, future):
        self._search_goal_handle = None
        self._doing_search       = False
        if self.ar_tag_detected:
            self.get_logger().info('AR tag found during search')
        else:
            self.get_logger().warn('Search complete — AR tag NOT found in search box')
        self.current_waypoint += 1

    # ── Mission tick ─────────────────────────────────────────

    def _mission_tick(self):
        if self._waiting_for_nav or self._doing_search:
            return

        if self.current_waypoint >= len(WAYPOINTS_LATLON):
            self.get_logger().info('Mission complete!')
            self._switch_mode('MANUAL')
            return

        wp   = WAYPOINTS_LATLON[self.current_waypoint]
        pose = self._latlon_to_map(wp[0], wp[1])

        is_ar_waypoint = (self.current_waypoint == len(WAYPOINTS_LATLON) - 1)

        if is_ar_waypoint and not self._doing_search:
            # Drive to the AR search area centre first
            self.get_logger().info(
                f'Navigating to AR search area (wp {self.current_waypoint})'
            )
            self._waiting_for_nav = True
            self._send_nav_goal(pose)
            self._doing_search = True

        elif self._doing_search and is_ar_waypoint:
            # Arrival callback cleared _waiting_for_nav; now start search
            self._doing_search = False   # will be set True again inside _start_search flow
            ar_pose = self._latlon_to_map(wp[0], wp[1])
            self._doing_search = True
            self._start_search(ar_pose)

        else:
            # Regular waypoint — drive there; object detection stops us via callback
            self.get_logger().info(
                f'Navigating to waypoint {self.current_waypoint}'
            )
            self.object_detected  = False
            self._waiting_for_nav = True
            self._send_nav_goal(pose)
            self.current_waypoint += 1


def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
