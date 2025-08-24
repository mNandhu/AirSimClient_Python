import airsim
import numpy as np
import open3d as o3d

# Constants
CAR_NAME = "Car1"


# Connect to the AirSim simulator
client = airsim.CarClient()  # Use CarClient for car simulation
client.confirmConnection()


def get_lidar_reading():
    # Switch Control to API
    client.enableApiControl(True, vehicle_name=CAR_NAME)

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

        # Yield Control
        client.enableApiControl(False, vehicle_name=CAR_NAME)

        return point_cloud, timestamp
    else:
        # Yield Control
        client.enableApiControl(False, vehicle_name=CAR_NAME)
        
        raise ValueError("No Lidar data available")


# Load XYZ from your AirSim CSV
point_cloud, timestamp = get_lidar_reading()
points = np.array(point_cloud)

# Create and visualize point cloud
pcd = o3d.geometry.PointCloud()
pcd.points = o3d.utility.Vector3dVector(points)

# Optional: color
# colors = np.tile(np.array([[0.2, 0.7, 1.0]], dtype=np.float32), (points.shape, 1))
# pcd.colors = o3d.utility.Vector3dVector(colors)

o3d.visualization.draw_geometries([pcd])
