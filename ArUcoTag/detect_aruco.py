import cv2
import numpy as np
import time

CAMERA_INDEX = 0

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

cap = cv2.VideoCapture(CAMERA_INDEX)
if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

print("ArUco detection started. Press Ctrl+C to quit.")

last_no_detection_print = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is not None:
            for marker_id in ids:
                print(f"Detected Marker ID: {marker_id[0]}")
        else:
            if time.time() - last_no_detection_print >= 0.75:
                print("No markers detected")
                last_no_detection_print = time.time()

except KeyboardInterrupt:
    print("Stopped by user")
finally:
    cap.release()
    print("Done.")
