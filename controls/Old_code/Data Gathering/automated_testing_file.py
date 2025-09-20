from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
import time
import matplotlib.pyplot as plt
import csv

# values for operation
toy_name = scanner.find_toy(toy_name = "SB-76B3")
speed = int(input("Speed of the ball: "))
heading = int(input("Heading: "))
operational_time = float(input("Number of seconds: "))

# place data gather values below
location_data = []
velocity_data = []
acceleration_data = []

orientation_data = []
gyroscope_data = []

time_data = []

with SpheroEduAPI(toy_name) as bolt:
    bolt.set_speed(speed)
    bolt.set_heading(heading)
    
    start_time = time.time()
    while (start_time + operational_time > time.time()):
        time_data.append(time.time())
        location_data.append(bolt.get_location())
        acceleration_data.append(bolt.get_acceleration())
        velocity_data.append(bolt.get_velocity())

        orientation_data.append(bolt.get_orientation())
        gyroscope_data.append(bolt.get_gyroscope())
        time.sleep(0.01)

print(location_data)
print(velocity_data)
print(acceleration_data)

x_loc = [loc_set["x"] for loc_set in location_data]
y_loc = [loc_set["y"] for loc_set in location_data]
# no z_loc
dist = [(loc_set["x"] ** 2 + loc_set["y"] ** 2) ** 0.5 for loc_set in location_data]

x_vel = [vel_set["x"] for vel_set in velocity_data]
y_vel = [vel_set["y"] for vel_set in velocity_data]
# no z_vel either

x_accel = [accel_set["x"] for accel_set in acceleration_data]
y_accel = [accel_set["y"] for accel_set in acceleration_data]
z_accel = [accel_set["z"] for accel_set in acceleration_data]

time_data = [moment - time_data[0] for moment in time_data]

# x values graphed
plt.plot(time_data, x_loc, label = "x")
plt.plot(time_data, x_vel, label = "x-velocity")
plt.plot(time_data, x_accel, label = "x-acceleration")
plt.xlabel("Time (s)")
plt.legend()
plt.show()

# y values graphed
plt.plot(time_data, y_loc, label = "y")
plt.plot(time_data, y_vel, label = "y-velocity")
plt.plot(time_data, y_accel, label = "y-acceleration")
plt.xlabel("Time (s)")
plt.legend()
plt.show()

print(orientation_data)
print(gyroscope_data)

pitch = [orientation_set["pitch"] for orientation_set in orientation_data]
yaw = [orientation_set["yaw"] for orientation_set in orientation_data]
roll = [orientation_set["roll"] for orientation_set in orientation_data]

gyro_x = [gyro_set["x"] for gyro_set in gyroscope_data]
gyro_y = [gyro_set["y"] for gyro_set in gyroscope_data]
gyro_z = [gyro_set["z"] for gyro_set in gyroscope_data]

if (input("Sucessful? ").lower() == "y"):
    with open('functionalities.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # figure out a way to write in values into csv for easy comparison
        for data_slice in zip(time_data, [speed] * len(time_data), x_loc, y_loc, dist, x_vel, y_vel, x_accel, y_accel, z_accel,
                            pitch, yaw, roll, gyro_x, gyro_y, gyro_z):
            print(data_slice)
            writer.writerows([list(data_slice)])
