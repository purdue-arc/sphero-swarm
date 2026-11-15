import pickle
import socket
from controls.Instruction import Instruction
from algorithms.sphero import Sphero
import pandas as pd
import matplotlib.pyplot as plt

SPHERO_SPEED_SLOPE = 20.973
SPHERO_SPEED_INTERCEPT = -1.293

port = 1235
sock = None 

sphero = Sphero(1, 0, 0, direction=1, trait="head")

distances = [i for i in range(1,3)]
actual_dist = []

def get_roll_duration(distance):
    '''
    gets the roll duration (seconds) of the sphero using the distance (inches)
    '''
        
    return (distance - SPHERO_SPEED_INTERCEPT) / SPHERO_SPEED_SLOPE



def _connect_controls(port: int) -> socket.socket:
    sock = socket.socket()
    sock.connect(("localhost", port))
    return sock

# main testing logic
for distance in distances:
    if sock is None:
        sock = _connect_controls(port)
    if sock is not None:
        duration = get_roll_duration(distance * 0.8)
        sock.send(pickle.dumps([Instruction(sphero.id, 1, 66, duration )]))
        sock.recv(1024)
        user_input = float(input("input actual distance: "))
        actual_dist.append(user_input)
        input("press enter to continue")

        
residuals = pd.DataFrame(actual_dist) - pd.DataFrame(distances)



plt.plot(distances, residuals)
plt.hlines(0, distances[0], distances[-1])
plt.show()

sock.close()
