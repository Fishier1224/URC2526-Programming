from setuptools import setup
import os
from glob import glob

package_name = 'rover'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        # Required ament_index marker
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Launch files
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        # Config files
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='Autonomous desert rover — Nav2 + Point-LIO + VESC odometry',
    license='MIT',
    entry_points={
        'console_scripts': [
            'serial_bridge_node = rover.serial_bridge_node:main',
            'joystick_node      = rover.joystick_node:main',
            'mission_node       = rover.mission_node:main',
            'gps_node           = rover.gps_node:main',
            'wheel_odom_node    = rover.wheel_odom_node:main',
        ],
    },
)
