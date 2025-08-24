from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import cv2

import airsim

# ---------------------------
# Simple configuration knobs
# ---------------------------
MODEL_NAME = "yolo12m.pt"  # e.g., yolo11n.pt, yolo11s.pt, or a custom .pt
CAMERAS = ["Front", "Right", "Back", "Left"]
CONF = 0.25
IOU = 0.45
DEVICE = "cuda:0"  # change to "cuda:0" if you have a working CUDA setup
SAVE_ANNOTATED = True
SAVE_DIR = Path("runs/recognize")
SHOW_WINDOW = True


def _response_to_bgr(res: airsim.ImageResponse) -> Optional[np.ndarray]:
    """
    Convert an AirSim ImageResponse (uncompressed, 8-bit) to an OpenCV BGR image.

    Handles both 3-channel (BGR) and 4-channel (BGRA) buffers.
    Returns None if the response is empty.
    """
    if res.width == 0 or res.height == 0 or not res.image_data_uint8:
        return None

    w, h = res.width, res.height
    img1d = np.frombuffer(res.image_data_uint8, dtype=np.uint8)

    # Try to infer channel count (3 or 4) from buffer size
    expected3 = w * h * 3
    expected4 = w * h * 4

    if img1d.size == expected3:
        img = img1d.reshape(h, w, 3)  # BGR (AirSim often returns BGR for uncompressed)
        return img
    elif img1d.size == expected4:
        img = img1d.reshape(h, w, 4)  # BGRA
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return bgr
    else:
        # Fallback: try to decode as compressed (rare here since compress=False)
        try:
            decoded = cv2.imdecode(img1d, cv2.IMREAD_COLOR)
            return decoded
        except Exception:
            return None


def _fetch_images(
    client: airsim.CarClient,
    cam_names: List[str],
    img_type: int = airsim.ImageType.Scene,
) -> Dict[str, Optional[np.ndarray]]:
    """Fetch images for all specified cameras in one RPC call, returning BGR images."""
    requests = [
        airsim.ImageRequest(name, img_type, pixels_as_float=False, compress=False)
        for name in cam_names
    ]
    responses = client.simGetImages(requests)
    images: Dict[str, Optional[np.ndarray]] = {}
    for name, res in zip(cam_names, responses):
        images[name] = _response_to_bgr(res)
    print("Fetched images for cameras:", cam_names)
    return images


def _load_model(model_name: str, device: str = "cpu"):
    from ultralytics import YOLO

    model = YOLO(model_name)
    # Ultralytics handles device internally; we can set via .predict(device=...)
    # Keep a tuple to return device string for later calls
    return model, device


def _run_detection(
    model,
    device: str,
    images: Dict[str, Optional[np.ndarray]],
    conf: float,
    iou: float,
) -> Dict[str, Optional[np.ndarray]]:
    """
    Run detection on all non-empty images and return annotated BGR images keyed by camera name.
    """
    # Prepare batch input while preserving camera order
    names: List[str] = []
    batch: List[np.ndarray] = []
    for name, img in images.items():
        if img is not None:
            names.append(name)
            batch.append(img)

    annotated: Dict[str, Optional[np.ndarray]] = {k: None for k in images.keys()}
    if not batch:
        return annotated

    # Run inference in batch
    results = model.predict(
        source=batch,
        conf=conf,
        iou=iou,
        device=device,
        verbose=False,
    )

    for name, res in zip(names, results):
        # res.plot() returns annotated image in BGR (np.ndarray)
        annotated[name] = res.plot()
    return annotated


def _save_images(
    images: Dict[str, Optional[np.ndarray]], save_dir: Path, prefix: str
) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    for name, img in images.items():
        if img is None:
            continue
        out_path = save_dir / f"{prefix}_{name}.jpg"
        cv2.imwrite(str(out_path), img)


def main():
    """Single-shot detection on AirSim car cameras using simple config above."""

    # Connect to AirSim Car client
    client = airsim.CarClient()
    client.confirmConnection()

    # Fetch images once
    cam_names = list(CAMERAS)
    images_bgr = _fetch_images(client, cam_names, airsim.ImageType.Scene)

    # Log any missing frames
    missing = [name for name, img in images_bgr.items() if img is None]
    if missing:
        print(f"[WARN] No image from: {', '.join(missing)}")

    # Load model and run inference
    model_obj, device_str = _load_model(MODEL_NAME, DEVICE)
    annotated_bgr = _run_detection(model_obj, device_str, images_bgr, CONF, IOU)

    # Save annotated outputs if requested
    if SAVE_ANNOTATED:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _save_images(annotated_bgr, SAVE_DIR, prefix=timestamp)
        print(f"[INFO] Saved annotated images to: {SAVE_DIR}")

    # Show results in a grid using matplotlib (convert BGR->RGB)
    if SHOW_WINDOW:
        try:
            import matplotlib.pyplot as plt

            cols = 2
            rows = max(1, int(np.ceil(len(cam_names) / cols)))
            fig, axes = plt.subplots(rows, cols, figsize=(14, 6))
            if isinstance(axes, np.ndarray):
                axes = axes.ravel()
            else:
                axes = [axes]

            for ax, name in zip(axes, cam_names):
                img = annotated_bgr.get(name)
                if img is not None:
                    ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                    ax.set_title(name)
                else:
                    ax.text(
                        0.5,
                        0.5,
                        f"{name}\nno image",
                        ha="center",
                        va="center",
                        fontsize=12,
                    )
                    ax.set_title(name)
                ax.axis("off")

            # Hide any unused subplots
            for ax in axes[len(cam_names) :]:
                ax.axis("off")

            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"[ERROR] Display failed: {e}")


if __name__ == "__main__":
    main()
