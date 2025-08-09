"""Hello Car demo: connect to AirSim Car, drive forward/right/reverse/brake cycles,
and capture depth and scene images to a temp directory."""

import airsim
import cv2
import numpy as np
import os
import time
import tempfile

# connect to the AirSim simulator
client = airsim.CarClient()
client.confirmConnection()
client.enableApiControl(True)
print("API Control enabled: %s" % client.isApiControlEnabled())
car_controls = airsim.CarControls()

tmp_dir = os.path.join(tempfile.gettempdir(), "airsim_car")
print("Saving images to %s" % tmp_dir)
try:
    os.makedirs(tmp_dir)
except OSError:
    if not os.path.isdir(tmp_dir):
        raise

for idx in range(3):
    # get state of the car
    car_state = client.getCarState()
    print(f"Speed {car_state.speed}, Gear {car_state.gear}")

    # go forward
    car_controls.throttle = 0.5
    car_controls.steering = 0
    client.setCarControls(car_controls)
    print("Go Forward")
    time.sleep(3)  # let car drive a bit

    # Go forward + steer right
    car_controls.throttle = 0.5
    car_controls.steering = 1
    client.setCarControls(car_controls)
    print("Go Forward, steer right")
    time.sleep(3)  # let car drive a bit

    # go reverse
    car_controls.throttle = -0.5
    car_controls.is_manual_gear = True
    car_controls.manual_gear = -1
    car_controls.steering = 0
    client.setCarControls(car_controls)
    print("Go reverse, steer right")
    time.sleep(3)  # let car drive a bit
    car_controls.is_manual_gear = False  # change back gear to auto
    car_controls.manual_gear = 0

    # apply brakes
    car_controls.brake = 1
    client.setCarControls(car_controls)
    print("Apply brakes")
    time.sleep(3)  # let car drive a bit
    car_controls.brake = 0  # remove brake

    # get camera images from the car
    responses = client.simGetImages(
        [
            airsim.ImageRequest(
                "0", airsim.ImageType.DepthVis
            ),  # depth visualization image
            airsim.ImageRequest(
                "1", airsim.ImageType.DepthPerspective, True
            ),  # depth in perspective projection
            airsim.ImageRequest(
                "1", airsim.ImageType.Scene
            ),  # scene vision image in png format
            airsim.ImageRequest("1", airsim.ImageType.Scene, False, False),
        ]
    )  # scene vision image in uncompressed RGB array
    print(f"Retrieved images: {len(responses)}")

    for response_idx, response in enumerate(responses):
        filename = os.path.join(tmp_dir, f"{idx}_{response.image_type}_{response_idx}")

        if response.pixels_as_float:
            # Depth/float image; write as PFM using AirSim helper
            print(f"Type {response.image_type} (float pixels)")
            airsim.write_pfm(
                os.path.normpath(filename + ".pfm"), airsim.get_pfm_array(response)
            )
        elif response.compress:  # png format
            print(f"Type {response.image_type} (compressed PNG)")
            airsim.write_file(
                os.path.normpath(filename + ".png"), response.image_data_uint8
            )
        else:  # uncompressed array
            print(f"Type {response.image_type} (raw RGB array)")
            # Convert raw bytes to numpy array
            img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)
            img_rgb = img1d.reshape(
                response.height, response.width, 3
            )  # reshape array to 3 channel image array H X W X 3
            cv2.imwrite(os.path.normpath(filename + ".png"), img_rgb)  # write to png

# restore to original state
client.reset()

client.enableApiControl(False)
