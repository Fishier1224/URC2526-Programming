import cv2
import cv2.aruco as aruco
import time
import os

# Create output directory
#os.makedirs("frames", exist_ok=True)

cap = cv2.VideoCapture(0)

dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

# Create detector ONCE (not every frame)
detector = cv2.aruco.ArucoDetector(dictionary, parameters)

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
            print("Detected IDs:", ids.flatten())

        # Save frame
        #cv2.imwrite(f"frames/frame_{frame_count:04d}.jpg", frame)
        frame_count += 1
        time.sleep(0.01)   # ~100 FPS cap

except KeyboardInterrupt:
    print("Stopped by user")

cap.release()
