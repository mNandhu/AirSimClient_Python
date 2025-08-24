import airsim
import numpy as np
import matplotlib.pyplot as plt
import cv2

client = airsim.CarClient()
client.confirmConnection()

# If needed (usually fine for cars too):
# client.enableApiControl(True)

# Camera names and desired image type
cam_names = ["Front", "Right", "Back", "Left"]
img_type = airsim.ImageType.Scene  # 0

# Build multi-image request (RGB, 8-bit, pixels_as_float=False)
requests = [
    airsim.ImageRequest(camera_name, img_type, pixels_as_float=False, compress=False)
    for camera_name in cam_names
]

# Get all images in a single call
responses = client.simGetImages(requests)


def response_to_rgb(res):
    # res.image_data_uint8 is a bytes object for uncompressed 8-bit RGB
    img1d = np.frombuffer(res.image_data_uint8, dtype=np.uint8)
    if res.width == 0 or res.height == 0 or img1d.size == 0:
        return None
    img_rgba = img1d.reshape(
        res.height, res.width, 3
    )  # when compress=False and pixels_as_float=False, AirSim returns 3 channels (RGB)
    # BGR->RGB swap; some builds return BGR:
    img_rgb = cv2.cvtColor(img_rgba, cv2.COLOR_BGR2RGB)
    # img_rgb = img_rgba
    return img_rgb


# Convert all responses
images = {name: response_to_rgb(res) for name, res in zip(cam_names, responses)}

# Optional: handle missing frames
for name, img in images.items():
    if img is None:
        print(f"Warning: {name} returned empty image")

# Plot as subplots (2x2)
fig, axes = plt.subplots(2, 2, figsize=(14, 8))
axes = axes.ravel()

for ax, name in zip(axes, cam_names):
    img = images[name]
    if img is not None:
        ax.imshow(img)
        ax.set_title(name)
    else:
        ax.text(0.5, 0.5, f"{name}\nno image", ha="center", va="center", fontsize=12)
        ax.set_title(name)
    ax.axis("off")

plt.tight_layout()
plt.show()
