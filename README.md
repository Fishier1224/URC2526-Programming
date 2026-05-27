# URC 2526 Programming — Jetson Branch 🤖

> Onboard software for the **University Rover Challenge 2025–2026** season, running on the NVIDIA Jetson platform.

---

## Table of Contents

- [Overview](#overview)
- [Hardware Requirements](#hardware-requirements)
- [Software Dependencies](#software-dependencies)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Running the Code](#running-the-code)
- [Contributing](#contributing)
- [Team](#team)

---

## Overview

This branch contains all code intended to run on the **NVIDIA Jetson** onboard computer of the rover. This includes perception, autonomy, communication with the base station, and integration with ROS 2.

> **Note:** This is the `main` branch. For other subsystems, check the other branches in this repo.

---

## Hardware Requirements

- All the sensors and actuators on the actual rover (GPS module, 2D Logitech Camera, Unitree L2 4D LiDAR, arm and claw and drive motors, Arduino Mega, Arduino Uno, and the MKR WAN (??)), NVIDIA Jetson Orin Nano (uses a 128gb microSD card; DO NOT lose this; in the event you fry the Jetson Orin Nano again can just reuse the card on a different Orin Nano), and a Windows OS laptop
- The XBox Controller

---

## Software Dependencies

| Dependency | Version |
|---|---|
| Ubuntu / JetPack | 22.04 / 6.x |
| ROS 2 | Humble |
| Python | 3.10+ |
| OpenCV | 4.x |
| PyTorch / TensorRT | (optional, for ML tasks) |

---

## Getting Started

### 1. Clone the repo

```bash
git clone -b jetson https://github.com/chouathenamo/URC2526-Programming.git
cd URC2526-Programming
```

### 2. Source ROS 2

```bash
source /opt/ros/humble/setup.bash
```

### 4. Build

```bash
colcon build
source install/setup.bash
```

---

## Project Structure

```
URC2526-Programming/
├── ArduinoCode/
│   ├── arduinoMegaCode.ino/        # Camera, object detection, ArUco tags
│   ├── arduinoUnoCode.ino/          # Navigation, path planning
│   ├── mkrwanReceiverRoverCode.ino/             # Base station communication
│   └── mkrwanSenderComputerCode.ino/          # Motor control, sensors
├── ArmSim/                # this is kind of irrelevant
├── ArUcoTag/              # this is also kind of irrelevant
├── ComputerCode/          # Code to run on Windows OS laptop
├── JetsonNanoCode/        # Code to run on Jetson Orin Nano
└── README.md
```

> Update this tree to reflect your actual structure.

---

## Running the Code from your Local Laptop
```bash
cd ComputerCode

```

### Launch everything

```bash
ros2 launch launch/rover_bringup.launch.py
```

### Run individual nodes

```bash
# Perception
ros2 run perception camera_node

# Autonomy
ros2 run autonomy nav_node
```

---

## Contributing

1. Branch off `main` for your feature: `git checkout -b feature/your-feature`
2. Make your changes and test on hardware
3. Open a pull request back to `main`
4. Merge into `main`

---

## Future Improvements to Make
- Autonomous has not been tested (due to hardware issues)
- Next year fix the wires on the rover to actually allow us to up the drive motor controllers to enable encoder reading (so we can actually run the autonomous nodes)
- Get electrical to come up with a better communication system (I personally am not a fan of MKR WAN at all); there should be further information about this in #electrical on Slack I believe.
- It's also a competition requirement to have camera feed data sent back to base; also get #electrical to source a new camera, or figure out the drone camera we have already.
- Currently drive wheels are out of commission (except one); will hopefully fix this before next school year.
- If I had more time permitting I would like to have implemented IK (inverse kinematics) for the rover arm so we don't have to manually control two separate linear actuators on the joystick; look into the controllers if we can get any odometry information for the linear actuators to implement this.
- Have not yet tested object detection model in a desert-like setting; it worked somewhat fine on the grass outside of SAC but would like to test in desert as it would probably perform better.
- Perhaps could also implement a Kalman Filter (or some other filtering technique) for smoother control and motion.
- If you enjoy coding front end interfaces could implement a QT interface for a more aesthetic and streamlined control interface on your laptop.
- (Not necessary but would be nice): see if you can get unlimited access to a monitor that is DisplayPort compatible, as this would allow you go directly into the Jetson Orin Nano's visual interface (and also see rviz simulations)

## Signing off
I believe in y'all and trust that you can build off this existing code framework and make the rover fully functional and much better! Don't hesitate to reach out to me if you have any questions or want advice on anything (related to the rover, grad school, academics, career-related things, or if you just want to chat). Good luck.

*University Rover Challenge 2025–2026 — [urc.marssociety.org](https://urc.marssociety.org)*