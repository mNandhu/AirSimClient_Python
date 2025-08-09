from dotenv import load_dotenv
import airsim
import os

load_dotenv()
CAR_NAME = os.getenv("CAR_NAME", "Car1")

client = airsim.CarClient()
client.confirmConnection()

# Yield control back to keyboard:
client.enableApiControl(False, vehicle_name=CAR_NAME)
