"""
ArUco Marker Generator
This script generates ArUco markers and saves them as images.
"""

import cv2
import numpy as np
import os


def generate_aruco_marker(marker_id, marker_size=200, save_path="aruco_markers"):
    """
    Generate a single ArUco marker.
    
    Args:
        marker_id: ID of the marker (0-249 for DICT_6X6_250)
        marker_size: Size of the marker in pixels
        save_path: Directory to save the marker images
    """
    # Create output directory if it doesn't exist
    os.makedirs(save_path, exist_ok=True)
    
    # Select ArUco dictionary
    # Common dictionaries:
    # - DICT_4X4_50: 4x4 bits, 50 markers
    # - DICT_5X5_100: 5x5 bits, 100 markers
    # - DICT_6X6_250: 6x6 bits, 250 markers (recommended)
    # - DICT_7X7_1000: 7x7 bits, 1000 markers
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    
    # Generate the marker
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
    
    # Save the marker
    filename = os.path.join(save_path, f"aruco_marker_{marker_id}.png")
    cv2.imwrite(filename, marker_image)
    print(f"Generated marker ID {marker_id}: {filename}")
    
    return marker_image


def generate_multiple_markers(num_markers=10, marker_size=200, save_path="aruco_markers"):
    """
    Generate multiple ArUco markers.
    
    Args:
        num_markers: Number of markers to generate
        marker_size: Size of each marker in pixels
        save_path: Directory to save the marker images
    """
    print(f"Generating {num_markers} ArUco markers...")
    
    for i in range(num_markers):
        generate_aruco_marker(i, marker_size, save_path)
    
    print(f"\nAll markers saved to '{save_path}/' directory")


def generate_marker_with_border(marker_id, marker_size=200, border_size=50, save_path="aruco_markers"):
    """
    Generate an ArUco marker with a white border (easier to detect).
    
    Args:
        marker_id: ID of the marker
        marker_size: Size of the marker in pixels (without border)
        border_size: Size of the white border in pixels
        save_path: Directory to save the marker images
    """
    os.makedirs(save_path, exist_ok=True)
    
    # Generate marker
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
    
    # Add white border
    total_size = marker_size + 2 * border_size
    bordered_image = np.ones((total_size, total_size), dtype=np.uint8) * 255
    bordered_image[border_size:border_size+marker_size, border_size:border_size+marker_size] = marker_image
    
    # Save the marker
    filename = os.path.join(save_path, f"aruco_marker_{marker_id}_bordered.png")
    cv2.imwrite(filename, bordered_image)
    print(f"Generated bordered marker ID {marker_id}: {filename}")
    
    return bordered_image


def main():
    """Main function to demonstrate marker generation."""
    print("ArUco Marker Generator")
    print("=" * 50)
    
    # Example 1: Generate a single marker
    print("\n1. Generating a single marker (ID: 0)...")
    generate_aruco_marker(marker_id=0, marker_size=200)
    
    # Example 2: Generate multiple markers
    print("\n2. Generating 5 markers (IDs: 0-4)...")
    generate_multiple_markers(num_markers=5, marker_size=200)
    
    # Example 3: Generate a marker with border (recommended for better detection)
    print("\n3. Generating a marker with white border (ID: 42)...")
    generate_marker_with_border(marker_id=42, marker_size=200, border_size=50)
    
    print("\n" + "=" * 50)
    print("Generation complete! Check the 'aruco_markers' folder.")
    print("\nTip: Print these markers on paper for use in computer vision applications.")


if __name__ == "__main__":
    main()
