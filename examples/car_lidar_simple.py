"""Simplified Lidar Data Capture"""

import airsim  # Import the AirSim library
import csv  # For writing to CSV
import time  # For timestamps or delays
import os  # For file and directory operations

# Connect to the AirSim simulator
client = airsim.CarClient()  # Use CarClient for car simulation
client.confirmConnection()

# Enable API control (if not already enabled)
client.enableApiControl(True, vehicle_name="Car1")


def save_to_csv(point_cloud, timestamp):
    os.makedirs("data/lidar", exist_ok=True)  # Create directory if it doesn't exist
    filename = f"data/lidar/lidar_points_{timestamp}.csv"
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["X", "Y", "Z"])  # Header
        writer.writerows(point_cloud)  # Write points
    print(f"Saved to {filename}")


# Main loop to read and process Lidar data
while True:
    # Get Lidar data (specify your Lidar name and vehicle)
    lidar_data = client.getLidarData(lidar_name="Lidar360", vehicle_name="Car1")

    if lidar_data.point_cloud:  # Check if points are available
        points = lidar_data.point_cloud  # Flat list: [x1,y1,z1, x2,y2,z2, ...]

        if not isinstance(points, list):
            print("Converting points to list")
            if isinstance(points, int) or isinstance(points, float):
                points = [points]
            points = list(points)

        timestamp = lidar_data.time_stamp

        print(f"Retrieved {len(points) // 3} points at timestamp {timestamp}")

        # Reshape into list of [x, y, z] tuples for easier handling
        point_cloud = [
            (points[i], points[i + 1], points[i + 2]) for i in range(0, len(points), 3)
        ]

        # Save to CSV (example function below)
        save_to_csv(point_cloud, timestamp)

    time.sleep(1)  # Adjust delay as needed (e.g., for continuous reading)
