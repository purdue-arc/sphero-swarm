from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import time

# values for operation
toy_name = scanner.find_toy(toy_name = "SB-B11D")
speed = 100
heading = 0
operational_time = 5.2

# place holder values below
location_data = []
velocity_data = []
acceleration_data = []

orientation_data = []
gyroscope_data = []

with SpheroEduAPI(toy_name) as bolt:
    bolt.set_speed(speed)
    bolt.set_heading(heading)
    
    start_time = time.time()
    while (start_time + operational_time > time.time()):
        location_data.append(bolt.get_location())
        acceleration_data.append(bolt.get_acceleration())
        velocity_data.append(bolt.get_velocity())

        orientation_data.append(bolt.get_orientation())
        gyroscope_data.append(bolt.get_gyroscope())
        time.sleep(1)

print(location_data)
print(velocity_data)
print(acceleration_data)

print(orientation_data)
print(gyroscope_data)
