import pickle
import socket
from controls.Instruction import Instruction
from algorithms.sphero import Sphero
import pandas as pd
import matplotlib.pyplot as plt

port = 1235
sock = None

durations = [round(number/12, 2) for number in range(1, 21)] # Type the durations you want to test here
speed = 66
distances = []
test_num = 1

sphero = Sphero(1, 0, 0, direction=1, trait="head")

def _connect_controls(port: int) -> socket.socket:
    sock = socket.socket()
    sock.connect(("localhost", port))
    return sock

for duration in durations:


    if sock is None:
        sock = _connect_controls(port)
    if sock is not None:
        sock.send(pickle.dumps([Instruction(sphero.id, 1, speed, duration)]))
        sock.recv(1024)

    user_input = input("Distance Rolled (in.): ")
    distances.append(float(user_input))

sock.close()
df = pd.DataFrame()
df["durations"] = durations
df["distances"] = distances
df["speeds"] = [speed for _ in distances]
df.to_csv("distance_mapping.csv", mode='a')

plt.plot(durations, distances)
plt.xlabel("duration")
plt.ylabel("distance (in)")
plt.show()