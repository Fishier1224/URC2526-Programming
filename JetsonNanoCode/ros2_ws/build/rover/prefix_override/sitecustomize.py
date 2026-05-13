import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/urcucla/Documents/URC2526-Programming/JetsonNanoCode/ros2_ws/install/rover'
