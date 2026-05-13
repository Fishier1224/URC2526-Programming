# jetson_bridge.py
# UDP receiver -> Arduino Mega/Uno bridge

import socket
import serial
import time
import re
import threading
import queue

LISTEN_IP   = "0.0.0.0"
LISTEN_PORT = 5010

MEGA_PORT = '/dev/mega'
UNO_PORT  = '/dev/uno'
BAUD_MEGA = 115200
BAUD_UNO  = 115200

mega = serial.Serial(MEGA_PORT, BAUD_MEGA, timeout=1)
uno  = serial.Serial(UNO_PORT,  BAUD_UNO,  timeout=1)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))

mega_queue = queue.Queue(maxsize=5)
uno_queue  = queue.Queue(maxsize=5)

def serial_writer(ser, q, name):
    while True:
        try:
            packet = q.get(timeout=1.0)
            ser.reset_output_buffer()
            ser.write((packet + '\n').encode('utf-8'))
        except queue.Empty:
            continue
        except serial.SerialException as e:
            print(f"{name} serial error: {e}")

threading.Thread(target=serial_writer, args=(mega, mega_queue, "Mega"), daemon=True).start()
threading.Thread(target=serial_writer, args=(uno,  uno_queue,  "Uno"),  daemon=True).start()

time.sleep(2)
print(f"Bridge active. Listening on {LISTEN_PORT}...")

packet_pattern = re.compile(r"(<[^>]+>)")

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
        data, addr = sock.recvfrom(65535)
        packet = data.decode('utf-8', errors='ignore').strip()

        match = packet_pattern.search(packet)
        if match:
            packet = match.group(1)
            parse_and_print(packet)
            try:
                mega_queue.put_nowait(packet)
            except queue.Full:
                pass
            try:
                uno_queue.put_nowait(packet)
            except queue.Full:
                pass

except KeyboardInterrupt:
    print("\nShutting down.")
    sock.close()
    mega.close()
    uno.close()
