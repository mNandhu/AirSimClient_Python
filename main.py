import airsim  # pip install airsim


def main():
    client = airsim.CarClient()  # for cars
    client.confirmConnection()  # blocks until connected
    client.enableApiControl(True)
    state = client.getCarState()
    print("Connected. Speed:", state.speed)


if __name__ == "__main__":
    main()
