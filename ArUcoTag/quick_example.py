"""
Quick Example: ArUco Marker Generation and Detection
This script demonstrates the complete workflow of generating and detecting ArUco markers.
"""

import cv2
import numpy as np
import os


def quick_demo():
    """Quick demonstration of ArUco marker generation and detection."""
    
    print("=" * 60)
    print("ArUco Marker Quick Example")
    print("=" * 60)
    
    # Step 1: Generate a marker
    print("\n[Step 1] Generating ArUco marker...")
    print("-" * 60)
    
    marker_id = 23
    marker_size = 200
    border_size = 50
    
    # Create output directory
    output_dir = "demo_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate marker
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
    
    # Add white border
    total_size = marker_size + 2 * border_size
    bordered_marker = np.ones((total_size, total_size), dtype=np.uint8) * 255
    bordered_marker[border_size:border_size+marker_size, border_size:border_size+marker_size] = marker_image
    
    # Save the marker
    marker_path = os.path.join(output_dir, f"demo_marker_{marker_id}.png")
    cv2.imwrite(marker_path, bordered_marker)
    
    print(f"✓ Generated marker with ID: {marker_id}")
    print(f"✓ Saved to: {marker_path}")
    print(f"✓ Size: {total_size}x{total_size} pixels")
    
    # Step 2: Create a test scene with the marker
    print("\n[Step 2] Creating test scene...")
    print("-" * 60)
    
    # Create a simple scene with the marker on a background
    scene = np.ones((600, 800, 3), dtype=np.uint8) * 255
    
    # Place the marker in the scene
    y_offset = 150
    x_offset = 200
    marker_bgr = cv2.cvtColor(bordered_marker, cv2.COLOR_GRAY2BGR)
    scene[y_offset:y_offset+total_size, x_offset:x_offset+total_size] = marker_bgr
    
    # Add text to the scene
    cv2.putText(scene, "ArUco Test Scene", (250, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(scene, f"Marker ID: {marker_id}", (250, 500), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    scene_path = os.path.join(output_dir, "test_scene.png")
    cv2.imwrite(scene_path, scene)
    
    print(f"✓ Created test scene")
    print(f"✓ Saved to: {scene_path}")
    
    # Step 3: Detect the marker in the scene
    print("\n[Step 3] Detecting ArUco marker...")
    print("-" * 60)
    
    # Convert to grayscale for detection
    gray = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY)
    
    # Detect markers
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, rejected = detector.detectMarkers(gray)
    
    if ids is not None:
        print(f"✓ Successfully detected {len(ids)} marker(s)!")
        for i, detected_id in enumerate(ids):
            print(f"  → Marker ID: {detected_id[0]}")
            
            # Get corner coordinates
            corner = corners[i][0]
            print(f"  → Corners:")
            for j, (x, y) in enumerate(corner):
                print(f"     Corner {j+1}: ({x:.1f}, {y:.1f})")
        
        # Draw detected markers on the scene
        detection_result = scene.copy()
        detection_result = cv2.aruco.drawDetectedMarkers(detection_result, corners, ids)
        
        # Add detection status text
        cv2.putText(detection_result, "DETECTED!", (250, 550), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        result_path = os.path.join(output_dir, "detection_result.png")
        cv2.imwrite(result_path, detection_result)
        print(f"\n✓ Detection visualization saved to: {result_path}")
        
    else:
        print("✗ No markers detected!")
        detection_result = scene
    
    # Step 4: Display results
    print("\n[Step 4] Displaying results...")
    print("-" * 60)
    
    # Create a comparison image
    comparison = np.hstack([
        cv2.resize(marker_bgr, (300, 300)),
        cv2.resize(scene, (300, 300)),
        cv2.resize(detection_result, (300, 300))
    ])
    
    # Add labels
    labeled_comparison = np.vstack([
        np.ones((50, comparison.shape[1], 3), dtype=np.uint8) * 240,
        comparison
    ])
    
    cv2.putText(labeled_comparison, "1. Generated", (30, 35), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(labeled_comparison, "2. Test Scene", (330, 35), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(labeled_comparison, "3. Detected", (630, 35), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    comparison_path = os.path.join(output_dir, "comparison.png")
    cv2.imwrite(comparison_path, labeled_comparison)
    
    print(f"✓ Comparison image saved to: {comparison_path}")
    
    # Display the result
    cv2.imshow('ArUco Quick Example - Press any key to close', labeled_comparison)
    print("\n✓ Displaying results in window...")
    print("  (Press any key to close)")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Generated marker ID: {marker_id}")
    print(f"✓ Detection successful: {ids is not None}")
    print(f"✓ Output files saved to: {output_dir}/")
    print("\nFiles created:")
    print(f"  • {marker_path}")
    print(f"  • {scene_path}")
    if ids is not None:
        print(f"  • {result_path}")
    print(f"  • {comparison_path}")
    print("\n" + "=" * 60)
    print("Next steps:")
    print("  • Print the marker and try detecting it with your webcam")
    print("  • Run detect_aruco.py for real-time detection")
    print("  • Try generate_aruco.py to create more markers")
    print("=" * 60)


def main():
    """Main function."""
    try:
        quick_demo()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure you have OpenCV installed:")
        print("  pip install opencv-python opencv-contrib-python numpy")


if __name__ == "__main__":
    main()
