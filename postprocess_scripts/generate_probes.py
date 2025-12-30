#!/usr/bin/env python3
"""
Generate probe points along a line between two points A and B.
"""

import numpy as np


def generate_probes_on_line(point_a, point_b, count):
    """
    Generate probe points along the line from point A to point B.
    
    Parameters:
    -----------
    point_a : tuple or list
        Coordinates (x, y, z) of point A
    point_b : tuple or list
        Coordinates (x, y, z) of point B
    count : int
        Number of probe points to generate
    
    Returns:
    --------
    list of tuples
        List of (x, y, z) coordinates of probe points
    """
    if count < 1:
        raise ValueError("Count must be at least 1")
    
    # Convert to numpy arrays for easy calculation
    a = np.array(point_a)
    b = np.array(point_b)
    
    # Generate evenly spaced points along the line
    probes = []
    for i in range(count):
        # Linear interpolation parameter from 0 to 1
        t = i / (count - 1) if count > 1 else 0
        point = a + t * (b - a)
        probes.append(tuple(point))
    
    return probes


def main():
    """Main function to get user input and generate probe points."""
    print("=== Generate Probe Points on Line ===\n")
    
    # Input point A
    print("Enter coordinates of point A:")
    ax, ay, az = 0.5, 0.01, 0.00
    point_a = (ax, ay, az)
    
    # Input point B
    print("\nEnter coordinates of point B:")
    bx,by,bz = 10.0, 0.01, 0.00
    point_b = (bx, by, bz)
    
    # Input count
    count = 100
    
    # Generate and print probe points
    print("\n=== Generated Probe Points ===")
    probes = generate_probes_on_line(point_a, point_b, count)
    
    for i, (x, y, z) in enumerate(probes):
        print(f"({x:.3f} {y:.3f} {z:.3f})")


if __name__ == "__main__":
    main()
