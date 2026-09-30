# IMU movement test: per Sphero, calibrate bias, roll, and log raw-IMU integration
# plus Sphero's onboard estimates to CSV for comparison with perception.

import csv
import math
import threading
import time

# NOT created by Claude: these helpers all come from your Controls_Test_Server.py
# (find_balls, generate_dict_map, address_sort, connect_multi_ball,
#  terminate_multi_ball, apply_led_colors, _toy_list_prefix)
from Controls_Test_Server import (
    find_balls, generate_dict_map, address_sort, connect_multi_ball,
    terminate_multi_ball, apply_led_colors, _toy_list_prefix,
)

GRAVITY = 9.81
DT = 0.03  # Sphero sensor stream updates about every 30 ms

CSV_HEADER = ["epoch", "t", "x_g", "y_g", "ax_ms2", "ay_ms2", "vx", "vy", "px", "py",
              "loc_x", "loc_y", "sph_vx", "sph_vy", "gyro_z", "yaw"]


# Created by Claude: reads one field from a Sphero sensor call, None if unavailable
def _get(fn, key):
    try:
        return fn()[key]
    except Exception:
        return None


# Created by Claude: average accelerometer X/Y while the ball is still (~3 s)
def imu_calibrate(sb, samples=100):
    xs, ys = [], []
    for _ in range(samples):
        a = sb.get_acceleration()
        xs.append(a["x"])
        ys.append(a["y"])
        time.sleep(DT)
    return sum(xs) / samples, sum(ys) / samples


# Created by Claude: roll the ball, double-integrate bias-corrected acceleration, return log + summary
def imu_measure(sb, bias, duration=5.0, drive_speed=60, heading=0):
    bx, by = bias
    vx = vy = px = py = peak = 0.0
    log = []

    # sb.roll blocks, so run it in a thread while sampling
    driver = None
    if drive_speed > 0:
        driver = threading.Thread(target=sb.roll, args=(heading, drive_speed, duration))
        driver.start()

    start = last = time.time()
    while time.time() - start < duration:
        now = time.time()
        dt, last = now - last, now

        a = sb.get_acceleration()
        ax = (a["x"] - bx) * GRAVITY
        ay = (a["y"] - by) * GRAVITY
        vx += ax * dt
        vy += ay * dt
        px += vx * dt
        py += vy * dt
        peak = max(peak, math.hypot(vx, vy))

        log.append((
            time.time(), now - start, a["x"], a["y"], ax, ay, vx, vy, px, py,
            _get(sb.get_location, "x"), _get(sb.get_location, "y"),
            _get(sb.get_velocity, "x"), _get(sb.get_velocity, "y"),
            _get(sb.get_gyroscope, "z"), _get(sb.get_orientation, "yaw"),
        ))
        time.sleep(DT)

    if driver:
        driver.join()

    return log, math.hypot(px, py), math.hypot(vx, vy), peak


# Created by Claude: connect, then per ball calibrate, roll, print summary, save CSV
def run_imu_movement(ball_names, duration=5.0, drive_speed=60, heading=0, runs=1):
    toys = find_balls(ball_names, 5)
    address_sort(toys, generate_dict_map(ball_names))

    sb_list = [None] * len(toys)
    try:
        connect_multi_ball(toys, sb_list, 10)
        apply_led_colors(sb_list)

        for toy, sb in zip(toys, sb_list):
            if sb is None:
                continue
            name = _toy_list_prefix(toy)
            for run in range(1, runs + 1):
                input("Place {} at the start position (run {}/{}), press Enter...".format(name, run, runs))
                bias = imu_calibrate(sb)
                log, dist, final_v, peak = imu_measure(sb, bias, duration, drive_speed, heading)
                print("{} run {}: distance {:.3f} m | final speed {:.3f} m/s | peak {:.3f} m/s".format(
                    name, run, dist, final_v, peak))
                with open("imu_{}_run{}.csv".format(name, run), "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(CSV_HEADER)
                    w.writerows(log)
    finally:
        terminate_multi_ball(sb_list)


if __name__ == "__main__":
    run_imu_movement(["SB-387B", "SB-C596", "SB-4D8E"], duration=2.0, drive_speed=60, heading=0, runs=1)