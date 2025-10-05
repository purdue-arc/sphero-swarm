from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
import time

import csv
import math

# Set your Sphero name here
toy_name = "SB-1840"

# Find and connect to the toy
toys = scanner.find_toys(toy_names=[toy_name])
if not toys:
    print("No toy found.")
    exit()

print(f"Found toy: {toys[0]}")
time.sleep(2)

speed = int(input("Speed of the ball (0-255): "))
heading = int(input("Heading (deg): "))
operational_time = float(input("Number of seconds to run: "))

# Data containers
location_data = []
velocity_data = []
acceleration_data = []
orientation_data = []
gyroscope_data = []
time_data = []
monotonic_data = []
seq_data = []
frame_id = 'base_link'

with SpheroEduAPI(toys[0]) as bolt:
    bolt.set_speed(speed)
    bolt.set_heading(heading)
    start_time = time.time()
    seq = 0
    try:
        while (start_time + operational_time > time.time()):
            now = time.time()
            time_data.append(now)
            monotonic_data.append(time.monotonic())
            seq_data.append(seq)
            seq += 1
            location_data.append(bolt.get_location())
            acceleration_data.append(bolt.get_acceleration())
            velocity_data.append(bolt.get_velocity())
            orientation_data.append(bolt.get_orientation())
            gyroscope_data.append(bolt.get_gyroscope())
            time.sleep(0.01)
    finally:
        bolt.set_speed(0)

# Write only Sphero-returned data to CSV
csv_filename = 'sphero_data_output.csv'
header = [
    "Time (s)",
    "X Location (mm)",
    "Y Location (mm)",
    "X Velocity (mm/s)",
    "Y Velocity (mm/s)",
    "X Acceleration (m/s^2)",
    "Y Acceleration (m/s^2)",
    "Z Acceleration (m/s^2)",
    "Pitch (deg)",
    "Yaw (deg)",
    "Roll (deg)",
    "Gyro X (deg/s)",
    "Gyro Y (deg/s)",
    "Gyro Z (deg/s)"
]
with open(csv_filename, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["# Sphero Data Output"])
    writer.writerow(["# Each row is a time step. Units are in the header."])
    writer.writerow(header)
    for i in range(len(time_data)):
        ax = acceleration_data[i]["x"] * 9.81
        ay = acceleration_data[i]["y"] * 9.81
        az = acceleration_data[i]["z"] * 9.81
        row = [
            f"{time_data[i]:.6f}",
            str(location_data[i]["x"]),
            str(location_data[i]["y"]),
            str(velocity_data[i]["x"]),
            str(velocity_data[i]["y"]),
            f"{ax:.6f}",
            f"{ay:.6f}",
            f"{az:.6f}",
            str(orientation_data[i]["pitch"]),
            str(orientation_data[i]["yaw"]),
            str(orientation_data[i]["roll"]),
            str(gyroscope_data[i]["x"]),
            str(gyroscope_data[i]["y"]),
            str(gyroscope_data[i]["z"])
        ]
        writer.writerow(row)

# Also write Kalman filter-ready CSV with correct unit conversions for EKF
kalman_csv = 'sphero_kalman_ready.csv'
kalman_header = [
    "timestamp (monotonic, s)",
    "seq",
    "dt_s",
    "theta (rad)",
    "roll (deg)",
    "pitch (deg)",
    "vel_x (mm/s)",
    "vel_y (mm/s)",
    "v_forward (m/s)",
    "gyro_z (rad/s)",
    "accel_x (m/s^2)",
    "accel_y (m/s^2)",
    "accel_z (m/s^2)"
]
yaw_rad = [o["yaw"] * math.pi / 180 for o in orientation_data]
roll_deg = [o["roll"] for o in orientation_data]
pitch_deg = [o["pitch"] for o in orientation_data]
vel_x = [v["x"] for v in velocity_data]
vel_y = [v["y"] for v in velocity_data]
vel_x_mps = [vx / 1000.0 for vx in vel_x]
vel_y_mps = [vy / 1000.0 for vy in vel_y]
v_forward = [vel_x_mps[i] * math.cos(yaw_rad[i]) + vel_y_mps[i] * math.sin(yaw_rad[i]) for i in range(len(vel_x))]
dt_s = [0.0] + [monotonic_data[i] - monotonic_data[i-1] for i in range(1, len(monotonic_data))]
gyro_z_rad = [g["z"] * math.pi / 180 for g in gyroscope_data]
# Accel in m/s^2 (raw in g, so multiply by 9.81)
accel_x_ms2 = [a["x"] * 9.81 for a in acceleration_data]
accel_y_ms2 = [a["y"] * 9.81 for a in acceleration_data]
accel_z_ms2 = [a["z"] * 9.81 for a in acceleration_data]
with open(kalman_csv, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["# Sphero Kalman Filter Data"])
    writer.writerow([
        "# Each row: [timestamp, seq, dt_s, theta, roll, pitch, vel_x, vel_y, v_forward, gyro_z, accel_x, accel_y, accel_z] -- all values are directly from Sphero sensors. Conversions: accel raw in g, *9.81 for m/s^2; gyro raw in deg/s, *pi/180 for rad/s; velocity raw in mm/s, /1000 for m/s; v_forward is projection onto heading (see code)."
    ])
    writer.writerow(kalman_header)
    for i in range(len(monotonic_data)):
        row = [
            f"{monotonic_data[i]:.6f}",
            str(seq_data[i]),
            f"{dt_s[i]:.6f}",
            f"{yaw_rad[i]:.6f}",
            f"{roll_deg[i]:.6f}",
            f"{pitch_deg[i]:.6f}",
            f"{vel_x[i]:.6f}",
            f"{vel_y[i]:.6f}",
            f"{v_forward[i]:.6f}",
            f"{gyro_z_rad[i]:.6f}",
            f"{accel_x_ms2[i]:.6f}",
            f"{accel_y_ms2[i]:.6f}",
            f"{accel_z_ms2[i]:.6f}"
        ]
        writer.writerow(row)
print(f"\nAll data written to {csv_filename} with only Sphero-returned values.")
print(f"All Kalman filter-ready data written to {kalman_csv} (EKF-friendly, Sphero-only fields, correct units).")
