from __future__ import annotations

from pathlib import Path
from typing import Any, List, Tuple

import numpy as np
import open3d as o3d
import airsim


# ---------------------------
# Simple configuration knobs
# ---------------------------
CAR_NAME = "Car1"
LIDAR_NAME = "Lidar360"

# Preprocessing
VOXEL_DOWNSAMPLE = 0.05  # meters; set 0 to disable
USE_OUTLIER_REMOVAL = True
NB_NEIGHBORS = 20
STD_RATIO = 2.0

# Clustering (Open3D DBSCAN)
DBSCAN_EPS = 0.5  # meters neighborhood radius
DBSCAN_MIN_POINTS = 10

# Visualization / Output
SHOW_BOUNDING_BOXES = True
SAVE_COLORED_PCD = True
SAVE_DIR = Path("runs/lidar")


def _to_np_points(flat_points: Any) -> np.ndarray:
    """Convert a flat list [x1,y1,z1, x2,y2,z2, ...] to Nx3 numpy array."""
    if isinstance(flat_points, np.ndarray):
        arr = flat_points
    else:
        # Ensure it's a list in case AirSim returns a non-list sequence
        if not isinstance(flat_points, list):
            if isinstance(flat_points, (int, float)):
                flat_points = [flat_points]
            flat_points = list(flat_points)
        arr = np.array(flat_points, dtype=np.float32)

    if arr.size % 3 != 0:
        # Pad or truncate to multiple of 3 to avoid reshape error
        arr = arr[: arr.size - (arr.size % 3)]

    points = arr.reshape(-1, 3)
    # Remove non-finite points
    finite = np.isfinite(points).all(axis=1)
    return points[finite]


def fetch_lidar_points(client: airsim.CarClient) -> Tuple[np.ndarray, int]:
    """Fetch a single LiDAR scan as Nx3 numpy array and return with timestamp."""
    client.enableApiControl(True, vehicle_name=CAR_NAME)
    try:
        data = client.getLidarData(lidar_name=LIDAR_NAME, vehicle_name=CAR_NAME)
        if not data.point_cloud:
            raise RuntimeError("No LiDAR data available")
        points = _to_np_points(data.point_cloud)
        return points, int(data.time_stamp)
    finally:
        client.enableApiControl(False, vehicle_name=CAR_NAME)


def preprocess_points(points: np.ndarray) -> o3d.geometry.PointCloud:
    """Create an Open3D PointCloud with optional voxel downsampling and outlier removal."""
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points.astype(np.float64))

    if VOXEL_DOWNSAMPLE and VOXEL_DOWNSAMPLE > 0:
        pcd = pcd.voxel_down_sample(voxel_size=VOXEL_DOWNSAMPLE)

    if USE_OUTLIER_REMOVAL:
        pcd, _ = pcd.remove_statistical_outlier(
            nb_neighbors=NB_NEIGHBORS, std_ratio=STD_RATIO
        )

    return pcd


def run_dbscan(pcd: o3d.geometry.PointCloud) -> np.ndarray:
    """Run DBSCAN clustering and return label array per point (-1 for noise)."""
    labels = np.array(
        pcd.cluster_dbscan(
            eps=DBSCAN_EPS, min_points=DBSCAN_MIN_POINTS, print_progress=False
        )
    )
    return labels


def colorize_by_cluster(
    pcd: o3d.geometry.PointCloud, labels: np.ndarray
) -> o3d.geometry.PointCloud:
    """Assign a distinct color per cluster; noise gets gray."""
    max_label = labels.max() if labels.size else -1
    colors = np.zeros((len(labels), 3), dtype=np.float32)

    if max_label >= 0:
        unique_labels = [cls for cls in np.unique(labels) if cls >= 0]
        # Generate HSV colors evenly spaced, convert to RGB
        for idx, cls in enumerate(unique_labels):
            hue = (idx / max(1, len(unique_labels))) % 1.0
            # Simple HSV->RGB manually
            rgb = _hsv_to_rgb(hue, 0.75, 1.0)
            colors[labels == cls] = rgb

    # Noise points -> light gray
    colors[labels == -1] = np.array([0.6, 0.6, 0.6], dtype=np.float32)

    pcd_colored = o3d.geometry.PointCloud(pcd)
    pcd_colored.colors = o3d.utility.Vector3dVector(colors.astype(np.float64))
    return pcd_colored


def _hsv_to_rgb(h: float, s: float, v: float) -> np.ndarray:
    """Convert HSV to RGB in [0,1]."""
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return np.array([r, g, b], dtype=np.float32)


def compute_bounding_boxes(
    pcd: o3d.geometry.PointCloud, labels: np.ndarray
) -> List[o3d.geometry.AxisAlignedBoundingBox]:
    boxes: List[o3d.geometry.AxisAlignedBoundingBox] = []
    unique_clusters = [cls for cls in np.unique(labels) if cls >= 0]
    pts = np.asarray(pcd.points)
    for idx, cls in enumerate(unique_clusters):
        cluster_pts = pts[labels == cls]
        if cluster_pts.shape[0] == 0:
            continue
        cp = o3d.geometry.PointCloud()
        cp.points = o3d.utility.Vector3dVector(cluster_pts)
        box = cp.get_axis_aligned_bounding_box()
        # Color the box similar to the cluster hue
        hue = (idx / max(1, len(unique_clusters))) % 1.0
        box.color = _hsv_to_rgb(hue, 0.9, 0.9).astype(float)
        boxes.append(box)
    return boxes


def main():
    # Connect to AirSim
    client = airsim.CarClient()
    client.confirmConnection()

    # Fetch LiDAR points
    try:
        points, ts = fetch_lidar_points(client)
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    print(f"[INFO] Retrieved {points.shape[0]} points at timestamp {ts}")

    # Preprocess
    pcd = preprocess_points(points)
    print(f"[INFO] Preprocessed point count: {np.asarray(pcd.points).shape[0]}")

    # Cluster
    labels = run_dbscan(pcd)
    num_clusters = int(labels.max() + 1) if labels.size and labels.max() >= 0 else 0
    num_noise = int((labels == -1).sum()) if labels.size else 0
    print(f"[INFO] Clusters: {num_clusters} | Noise points: {num_noise}")

    # Colorize and optional save
    pcd_colored = colorize_by_cluster(pcd, labels)
    if SAVE_COLORED_PCD:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        out_path = SAVE_DIR / "clusters_colored.pcd"
        o3d.io.write_point_cloud(str(out_path), pcd_colored)
        print(f"[INFO] Saved colored point cloud: {out_path}")

    # Bounding boxes
    geometries = [pcd_colored]
    if SHOW_BOUNDING_BOXES and num_clusters > 0:
        boxes = compute_bounding_boxes(pcd, labels)
        geometries.extend(boxes)

    # Visualize
    o3d.visualization.draw_geometries(geometries)  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
