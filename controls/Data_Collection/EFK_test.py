from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
import time

import csv
import math
import logging
import argparse
from datetime import datetime
from pathlib import Path
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _safe_get(d, key, default=0.0, sample_index=None, name=""):
    if not isinstance(d, dict):
        logging.debug("Expected dict for %s at index %s, got %s", name, sample_index, type(d))
        return default
    if key not in d:
        logging.debug("Missing key '%s' in %s at index %s; using default %s", key, name, sample_index, default)
    return d.get(key, default)


# Module-level state to support per-sphero sampling (used by server when importing)
_KALMAN_LAST_TIME = {}
_KALMAN_SEQ = {}
KALMAN_DEFAULT_PATH = Path(__file__).resolve().parent / 'sphero_kalman_ready.csv'
DATA_DEFAULT_PATH = Path(__file__).resolve().parent / 'sphero_data_output.csv'


def append_kalman_row(sphero_idx: int,
                      monotonic_ts: float,
                      seq: int,
                      dt: float,
                      orientation: dict,
                      velocity: dict,
                      acceleration: dict,
                      gyroscope: dict,
                      out_path: Path = None):

    if out_path is None:
        out_path = KALMAN_DEFAULT_PATH

    # Prepare conversions
    yaw_rad = (_safe_get(orientation, 'yaw', 0.0) ) * math.pi / 180.0
    roll_deg = _safe_get(orientation, 'roll', 0.0)
    pitch_deg = _safe_get(orientation, 'pitch', 0.0)
    vel_x = _safe_get(velocity, 'x', 0.0)
    vel_y = _safe_get(velocity, 'y', 0.0)
    vel_x_mps = vel_x / 1000.0
    vel_y_mps = vel_y / 1000.0
    v_forward = vel_x_mps * math.cos(yaw_rad) + vel_y_mps * math.sin(yaw_rad)
    gyro_z_rad = _safe_get(gyroscope, 'z', 0.0) * math.pi / 180.0
    accel_x_ms2 = _safe_get(acceleration, 'x', 0.0) * 9.81
    accel_y_ms2 = _safe_get(acceleration, 'y', 0.0) * 9.81
    accel_z_ms2 = _safe_get(acceleration, 'z', 0.0) * 9.81

    header = [
        'sphero_idx',
        'timestamp (monotonic, s)',
        'seq',
        'dt_s',
        'theta (rad)',
        'roll (deg)',
        'pitch (deg)',
        'vel_x (mm/s)',
        'vel_y (mm/s)',
        'v_forward (m/s)',
        'gyro_z (rad/s)',
        'accel_x (m/s^2)',
        'accel_y (m/s^2)',
        'accel_z (m/s^2)'
    ]

    write_header = not out_path.exists()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(out_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if write_header:
                writer.writerow(["# Sphero Kalman Filter Data"])
                writer.writerow(["# sphero_idx is the first column to attribute rows to a sphero index in sb_list"]) 
                writer.writerow(header)

            row = [
                str(sphero_idx),
                f"{monotonic_ts:.6f}",
                str(seq),
                f"{dt:.6f}",
                f"{yaw_rad:.6f}",
                f"{roll_deg:.6f}",
                f"{pitch_deg:.6f}",
                f"{vel_x:.6f}",
                f"{vel_y:.6f}",
                f"{v_forward:.6f}",
                f"{gyro_z_rad:.6f}",
                f"{accel_x_ms2:.6f}",
                f"{accel_y_ms2:.6f}",
                f"{accel_z_ms2:.6f}"
            ]
            writer.writerow(row)
    except Exception:
        logging.exception("Failed to append kalman row for sphero %s to %s", sphero_idx, out_path)


def reset_output_files(out_dir: Path = None):
    """Overwrite both data and kalman CSV files with headers.

    Use this at the start of a session so subsequent per-sphero calls append
    a fresh file. If out_dir is provided, files are written there; otherwise
    the Data_Collection folder is used.
    """
    if out_dir is None:
        out_dir = Path(__file__).resolve().parent

    # write sphero_data_output header (empty content)
    data_header = [
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
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with open(out_dir / DATA_DEFAULT_PATH.name, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["# Sphero Data Output"])
            writer.writerow(["# Each row is a time step. Units are in the header."])
            writer.writerow(data_header)
    except Exception:
        logging.exception("Failed to reset sphero_data_output file at %s", out_dir / DATA_DEFAULT_PATH.name)

    # write kalman header (overwrite)
    kalman_header = [
        'sphero_idx',
        'timestamp (monotonic, s)',
        'seq',
        'dt_s',
        'theta (rad)',
        'roll (deg)',
        'pitch (deg)',
        'vel_x (mm/s)',
        'vel_y (mm/s)',
        'v_forward (m/s)',
        'gyro_z (rad/s)',
        'accel_x (m/s^2)',
        'accel_y (m/s^2)',
        'accel_z (m/s^2)'
    ]
    try:
        with open(out_dir / KALMAN_DEFAULT_PATH.name, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["# Sphero Kalman Filter Data"])
            writer.writerow(["# sphero_idx is the first column to attribute rows to a sphero index in sb_list"]) 
            writer.writerow(kalman_header)
    except Exception:
        logging.exception("Failed to reset sphero_kalman_ready file at %s", out_dir / KALMAN_DEFAULT_PATH.name)


def sample_and_append(sb, sphero_idx: int, out_path: Path = None):
    """Convenience: read sensors from a SpheroEduAPI-like object and append one row.

    Maintains internal per-sphero seq and last-time to compute dt if called repeatedly.
    """
    now = time.monotonic()
    last = _KALMAN_LAST_TIME.get(sphero_idx, None)
    dt = 0.0 if last is None else (now - last)
    _KALMAN_LAST_TIME[sphero_idx] = now
    seq = _KALMAN_SEQ.get(sphero_idx, 0)
    _KALMAN_SEQ[sphero_idx] = seq + 1

    # Read sensor values from sb object; tolerate missing attributes via _safe_get
    try:
        location = sb.get_location()
        velocity = sb.get_velocity()
        acceleration = sb.get_acceleration()
        orientation = sb.get_orientation()
        gyroscope = sb.get_gyroscope()
    except Exception:
        logging.exception("Failed to sample sb for sphero_idx %s", sphero_idx)
        return

    append_kalman_row(sphero_idx=sphero_idx,
                      monotonic_ts=now,
                      seq=seq,
                      dt=dt,
                      orientation=orientation,
                      velocity=velocity,
                      acceleration=acceleration,
                      gyroscope=gyroscope,
                      out_path=out_path)


def main(simulate: bool = False):
    # Set your Sphero name here
    toy_name = "SB-1840"

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

    if simulate:
        logging.info("Running in simulate mode: will generate fake sensor data for testing.")
        N = 100
        seq = 0
        start_time = time.time()
        for i in range(N):
            now = start_time + i * 0.01
            time_data.append(now)
            monotonic_data.append(i * 0.01)
            seq_data.append(seq)
            seq += 1
            # Simple synthetic data matching expected shapes/keys
            location_data.append({"x": 1000.0 + i * 1.0, "y": 500.0 - i * 0.5})
            velocity_data.append({"x": 1000.0 + i * 2.0, "y": 200.0 - i * 1.0})
            acceleration_data.append({"x": 0.02 + i * 0.001, "y": -0.01 + i * 0.0005, "z": 0.0})
            orientation_data.append({"pitch": 0.0 + i * 0.01, "yaw": 0.0 + i * 0.5, "roll": 0.0})
            gyroscope_data.append({"x": 0.0, "y": 0.0, "z": 1.0 + i * 0.01})
    else:
        # Find and connect to the toy
        toys = scanner.find_toys(toy_names=[toy_name])
        if not toys:
            logging.error("No toy found.")
            sys.exit(1)

        logging.info("Found toy: %s", toys[0])
        time.sleep(2)

        try:
            speed = int(input("Speed of the ball (0-255): "))
            heading = int(input("Heading (deg): "))
            operational_time = float(input("Number of seconds to run: "))
        except Exception:
            logging.error("Invalid input; exiting.")
            sys.exit(1)

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

    # Basic guard: ensure we have data
    if len(monotonic_data) == 0:
        logging.warning("No samples collected; no CSV files will be written.")
        return

    # Output files: write fixed filenames into the script's folder so runs
    # always overwrite the same two CSVs in controls/Data_Collection
    out_dir = Path(__file__).resolve().parent
    kalman_csv = 'sphero_kalman_ready.csv'

    # Write only Sphero-returned data to CSV (formatted)
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

    # Also write Kalman filter-ready CSV with correct unit conversions for EKF
    # prepend sphero_idx so server/appended rows are attributed
    kalman_header = [
        "sphero_idx",
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

    yaw_rad = [(_safe_get(o, 'yaw', 0.0, i, 'orientation')) * math.pi / 180 for i, o in enumerate(orientation_data)]
    roll_deg = [_safe_get(o, 'roll', 0.0, i, 'orientation') for i, o in enumerate(orientation_data)]
    pitch_deg = [_safe_get(o, 'pitch', 0.0, i, 'orientation') for i, o in enumerate(orientation_data)]
    vel_x = [_safe_get(v, 'x', 0.0, i, 'velocity') for i, v in enumerate(velocity_data)]
    vel_y = [_safe_get(v, 'y', 0.0, i, 'velocity') for i, v in enumerate(velocity_data)]
    vel_x_mps = [vx / 1000.0 for vx in vel_x]
    vel_y_mps = [vy / 1000.0 for vy in vel_y]
    v_forward = [vel_x_mps[i] * math.cos(yaw_rad[i]) + vel_y_mps[i] * math.sin(yaw_rad[i]) for i in range(len(vel_x))]
    dt_s = [0.0] + [monotonic_data[i] - monotonic_data[i-1] for i in range(1, len(monotonic_data))]
    gyro_z_rad = [(_safe_get(g, 'z', 0.0, i, 'gyroscope')) * math.pi / 180 for i, g in enumerate(gyroscope_data)]
    # Accel in m/s^2 (raw in g, so multiply by 9.81)
    accel_x_ms2 = [(_safe_get(a, 'x', 0.0, i, 'acceleration')) * 9.81 for i, a in enumerate(acceleration_data)]
    accel_y_ms2 = [(_safe_get(a, 'y', 0.0, i, 'acceleration')) * 9.81 for i, a in enumerate(acceleration_data)]
    accel_z_ms2 = [(_safe_get(a, 'z', 0.0, i, 'acceleration')) * 9.81 for i, a in enumerate(acceleration_data)]

    with open(out_dir / kalman_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["# Sphero Kalman Filter Data"])
        writer.writerow([
            "# Each row: [timestamp, seq, dt_s, theta, roll, pitch, vel_x, vel_y, v_forward, gyro_z, accel_x, accel_y, accel_z] -- all values are directly from Sphero sensors. Conversions: accel raw in g, *9.81 for m/s^2; gyro raw in deg/s, *pi/180 for rad/s; velocity raw in mm/s, /1000 for m/s; v_forward is projection onto heading (see code)."
        ])
        writer.writerow(kalman_header)
        for i in range(len(monotonic_data)):
            # sphero_idx = -1 for batch/script-run rows
            row = [
                str(-1),
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

    logging.info("All Kalman filter-ready data written to %s (EKF-friendly, Sphero-only fields, correct units).", out_dir / kalman_csv)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collect Sphero data and write CSVs. Use --simulate to run without hardware')
    parser.add_argument('--simulate', action='store_true', help='Run using synthetic data (no Sphero hardware required)')
    args = parser.parse_args()
    main(simulate=args.simulate)
