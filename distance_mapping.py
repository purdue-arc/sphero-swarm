import pickle
import socket
from controls.Instruction import Instruction
from algorithms.sphero import Sphero
import pandas as pd
import matplotlib.pyplot as plt

port = 1235
sock = None

durations = [0.5, 0.8, 1.1] # Type the durations you want to test here
speeds = [50, 60, 70] # Type the speeds you want to test
data = [] # Stores each result in the format (duration, speed, distance)

sphero = Sphero(1, 0, 0, direction=1, trait="head")

def _connect_controls(port: int) -> socket.socket:
    sock = socket.socket()
    sock.connect(("localhost", port))
    return sock

for speed in speeds:
    for duration in durations:

        if sock is None:
            sock = _connect_controls(port)
        if sock is not None:
            sock.send(pickle.dumps(Instruction(sphero.id, 1, speed, duration)))
            sock.recv(1024)

        user_input = input("Distance Rolled (in.): ")
        if not str.isnumeric(user_input):
            break
        else:
            data.append((duration, speed, float(user_input)))

sock.close()


# df = pd.DataFrame()
# df["durations"] = durations
# df["speeds"] = speeds
# df["distances"] = distances
# df.to_csv("distance_mapping.csv")

with open("Distance_Mapping_Data.txt", "a") as file:
    file.write(str(data) + "\n")

fig, (ax1, ax2) = plt.subplots(2)

for speed in speeds:
    plot_durations = []
    plot_distances = []
    for element in data:
        if element(1) == speed:
            plot_durations.append(element(0))
            plot_distances.append(element(2))
    ax1.plot(plot_durations, plot_distances, label=f"Speed = {speed}")
ax1.xlabel("duration")
ax1.ylabel("distance (in)")

for duration in durations:
    plot_speeds = []
    plot_distances = []
    for element in data:
        if element(0) == duration:
            plot_speeds.append(element(1))
            plot_distances.append(element(2))
    ax2.plot(plot_durations, plot_speeds, label=f"Duration = {duration}")
ax2.xlabel("speed")
ax2.ylabel("distance (in)")

plt.show()