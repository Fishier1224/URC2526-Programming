"""
ArUco Marker Detector
This script detects ArUco markers in images or from a webcam feed.
"""

import cv2
import numpy as np


def detect_aruco_image(image_path):
    """
    Detect ArUco markers in a static image.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Image with detected markers drawn
    """
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return None
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Select ArUco dictionary
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    parameters = cv2.aruco.DetectorParameters()
    
    # Detect markers
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, rejected = detector.detectMarkers(gray)
    
    # Draw detected markers
    if ids is not None:
        print(f"Detected {len(ids)} marker(s):")
        for i, marker_id in enumerate(ids):
            print(f"  - Marker ID: {marker_id[0]}")
            
        # Draw markers on the image
        image = cv2.aruco.drawDetectedMarkers(image, corners, ids)
    else:
        print("No markers detected in the image.")
    
    return image


def detect_aruco_webcam():
    """
    Detect ArUco markers in real-time from webcam.
    Press 'q' to quit.
    """
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    # Select ArUco dictionary
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    print("Webcam started. Press 'q' to quit.")
    
    while True:
        # Capture frame
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            break
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect markers
        corners, ids, rejected = detector.detectMarkers(gray)
        
        # Draw detected markers
        if ids is not None:
            frame = cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            
            # Display marker information on frame
            for i, marker_id in enumerate(ids):
                # Get the center of the marker
                corner = corners[i][0]
                center_x = int(np.mean(corner[:, 0]))
                center_y = int(np.mean(corner[:, 1]))
                
                # Draw marker ID
                cv2.putText(frame, f"ID: {marker_id[0]}", 
                           (center_x - 30, center_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Display the frame
        cv2.imshow('ArUco Marker Detection', frame)
        
        # Check for 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Webcam closed.")


def detect_with_pose_estimation(image_path, marker_size=0.05, camera_matrix=None, dist_coeffs=None):
    """
    Detect ArUco markers and estimate their 3D pose.
    
    Args:
        image_path: Path to the image file
        marker_size: Real-world size of the marker in meters (e.g., 0.05 for 5cm)
        camera_matrix: Camera calibration matrix (3x3)
        dist_coeffs: Distortion coefficients (5x1 or 8x1)
    
    Returns:
        Image with detected markers and pose axes drawn
    """
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return None
    
    # If no camera calibration provided, use default values
    if camera_matrix is None:
        # These are approximate values - for accurate results, calibrate your camera
        focal_length = image.shape[1]
        center = (image.shape[1] / 2, image.shape[0] / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=float)
    
    if dist_coeffs is None:
        dist_coeffs = np.zeros((5, 1))
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Select ArUco dictionary
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Detect markers
    corners, ids, rejected = detector.detectMarkers(gray)
    
    if ids is not None:
        print(f"Detected {len(ids)} marker(s) with pose estimation:")
        
        # Draw detected markers
        image = cv2.aruco.drawDetectedMarkers(image, corners, ids)
        
        # Estimate pose for each marker
        for i in range(len(ids)):
            # Estimate pose
            rvec, tvec, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners[i], marker_size, camera_matrix, dist_coeffs
            )
            
            # Draw axis
            cv2.drawFrameAxes(image, camera_matrix, dist_coeffs, rvec, tvec, marker_size * 0.5)
            
            print(f"  - Marker ID {ids[i][0]}:")
            print(f"    Translation: {tvec[0][0]}")
            print(f"    Rotation: {rvec[0][0]}")
    else:
        print("No markers detected.")
    
    return image


def main():
    """Main function to demonstrate marker detection."""
    print("ArUco Marker Detector")
    print("=" * 50)
    print("\nChoose detection mode:")
    print("1. Detect from image file")
    print("2. Detect from webcam (real-time)")
    print("3. Detect with pose estimation")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == "1":
        image_path = input("Enter image path: ")
        result = detect_aruco_image(image_path)
        if result is not None:
            cv2.imshow('Detected Markers', result)
            print("\nPress any key to close the window...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    
    elif choice == "2":
        detect_aruco_webcam()
    
    elif choice == "3":
        image_path = input("Enter image path: ")
        marker_size = float(input("Enter marker size in meters (e.g., 0.05 for 5cm): "))
        result = detect_with_pose_estimation(image_path, marker_size)
        if result is not None:
            cv2.imshow('Detected Markers with Pose', result)
            print("\nPress any key to close the window...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()
