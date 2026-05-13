import cv2
import cv2.aruco as aruco
import serial
import subprocess
import time
import socket

# -------------------- Stop teleop service --------------------
subprocess.run(["sudo", "systemctl", "stop", "jetson_bridge.service"])
time.sleep(1)

#SERIAL_PORT = "/dev/mkr_wan"
#SERIAL_BAUD = 115200

#ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
#time.sleep(2)  # wait for Arduino to reset
#print(f"Serial open on {SERIAL_PORT}")


#UDP for now
PC_IP   = "192.168.8.185"
PC_PORT = 5011
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

cap = cv2.VideoCapture(0)

dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(dictionary, parameters)

def send_detection(msg):
    #ser.write(f"<{msg}>\n".encode())
    label = f"<{msg}>\n"
    sock.sendto(label.encode(), (PC_IP, PC_PORT))

frame_count = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
            flat_ids = ids.flatten()
            print("Detected IDs:", flat_ids)
            for tag_id in flat_ids:
                send_detection(f"ArUco:{tag_id}")

        frame_count += 1
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Stopped by user")
finally:
    cap.release()
    #ser.close()
    sock.close()
    subprocess.run(["sudo", "systemctl", "start", "jetson_bridge.service"])
    print("Done.")
