import pickle
import socket
from controls.Instruction import Instruction
from algorithms.sphero import Sphero
import pandas as pd
import matplotlib.pyplot as plt
from gui_driver import _perception_request
import math
import time
import zmq
import numpy as np

port = 1235
sock = None
ROLL_STRAIGHT_INCH = 10.0
df = pd.DataFrame(columns=["durations", "distances", "speeds"])
plt.xlabel("duration")
plt.ylabel("distance (in)")
plt.ion()

# durations = [round(number/12, 2) for number in range(1, 21)] # Type the durations you want to test here
reps = 9
durations = []
for duration in np.linspace(1.0, 1.5, num=6):
    durations += [round(float(duration), 2)] * reps

speed = 66
distances = []
test_num = 1

test_sphero = Sphero(1, 0, 0, direction=1, trait="head")

def perception_init(message):
    """Short-lived socket keeps a missing perception process from blocking rolls."""
    sock = zmq.Context.instance().socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.setsockopt(zmq.RCVTIMEO, 1000)
    sock.setsockopt(zmq.SNDTIMEO, 1000)
    try:
        sock.connect("tcp://127.0.0.1:5555")
        if isinstance(message, str):
            sock.send_string(message)  # plain commands, e.g. "coords"
        else:
            sock.send_json(message)
        return sock.recv_string()
    except zmq.ZMQError:
        return None
    finally:
        sock.close()
perception_init("init")

def _connect_controls(port: int) -> socket.socket:
    sock = socket.socket()
    sock.connect(("localhost", port))
    return sock

def get_coords():
    coords = _perception_request("coords")
    print(coords)
    for sphero in coords.get("spheros", []):
        if sphero["ID"] == test_sphero.id-1:
            x_pos = sphero["X"]
            y_pos = sphero["Y"]
            return (x_pos, y_pos)
    return (-999, -999)
count = 0
for duration in durations:
    count+=1

    if sock is None:
        sock = _connect_controls(port)
        # sock.send(pickle.dumps([Instruction(test_sphero.id, 1, speed, 1.5)]))
        # time.sleep(5)
    if sock is not None:
        start_x, start_y = get_coords()
        print(f"start X:{start_x}, start Y:{start_y}")
        
        
        sock.send(pickle.dumps([Instruction(test_sphero.id, 1, speed, duration)]))
        sock.recv(1024)
        
        time.sleep(duration * 1.25 + 2)
        end_x, end_y = get_coords()
        print(f"end X:{end_x}, end Y:{end_y}")
            
        distance = ROLL_STRAIGHT_INCH * math.hypot((end_x - start_x), (end_y - start_y))
        print(f"distance: {distance}")
        sock.send(pickle.dumps([Instruction(test_sphero.id, 2, (-180.0 if count % 2 == 0 else 180.0), 0.5)]))
        time.sleep(1.2)

    # user_input = input("Distance Rolled (in.): ")
    # a = input("Enter to continue")
        distances.append(distance)
        new_data = pd.DataFrame({"durations": [duration], "distances": [distance], "speeds": [speed]}, index=[count])
        # df = pd.concat([df, new_data])
        new_data.to_csv("distance_mapping/distance_mapping_test_data/test_01.csv", mode='a', header=(True if count == 1 else False))
        plt.scatter(durations[:count], distances)
        plt.pause(0.001)           # Tiny pause required to yield control to the GUI

sock.close()

plt.ioff()
plt.show()