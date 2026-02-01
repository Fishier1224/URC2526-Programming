# jetson_bridge.py
# MKR WAN receiver -> Arduino Mega bridge

import serial
import time
import re

MKR_PORT  = '/dev/ttyACM0'  # MKR WAN receiver — check with: ls /dev/ttyACM*
MEGA_PORT = '/dev/ttyACM1'  # Arduino Mega
BAUD_MKR  = 115200
BAUD_MEGA = 115200

mkr_wan = serial.Serial(MKR_PORT, BAUD_MKR, timeout=1)
mega    = serial.Serial(MEGA_PORT, BAUD_MEGA, timeout=1)

time.sleep(2)
print("Bridge active. Waiting for LoRa controller data...")

packet_pattern = re.compile(r"(<[^>]+>)")
buf = ""

def parse_and_print(packet):
    inner = packet.strip("<>")
    fields = inner.split(",")
    if len(fields) != 14:
        return
    lx, ly, rx, ry = [float(fields[i]) for i in range(4)]
    a, b, x, y     = [int(fields[i]) for i in range(4, 8)]
    dpx, dpy        = int(fields[8]), int(fields[9])
    lb, rb, lt, rt  = [int(fields[i]) for i in range(10, 14)]
    print(f"L({lx:.2f},{ly:.2f}) R({rx:.2f},{ry:.2f}) "
          f"A:{a} B:{b} X:{x} Y:{y} "
          f"DPAD({dpx},{dpy}) LB:{lb} RB:{rb} LT:{lt} RT:{rt}")

try:
    while True:
        if mkr_wan.in_waiting > 0:
            buf += mkr_wan.read(mkr_wan.in_waiting).decode('utf-8', errors='ignore')

        match = packet_pattern.search(buf)
        if match:
            packet = match.group(1)
            buf    = buf[match.end():]

            parse_and_print(packet)
            mega.write((packet + '\n').encode('utf-8'))

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nShutting down.")
    mkr_wan.close()
    mega.close()
