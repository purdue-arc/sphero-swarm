import pickle
import socket
from Instruction import Instruction
import time

s = socket.socket()
port = 1235
s.connect(('localhost', port))
# accept values about balls connected
valid_sphero_ids = pickle.loads(s.recv(1024))

commands_array = []
# make spheros red
print("Red")
for id in valid_sphero_ids:
    commands_array.append(Instruction(id, 0, 255, 0, 0))
s.send(pickle.dumps(commands_array))
buffer = s.recv(1024).decode()

commands_array = []
# add waiting for spheros
print("Wait")
for id in valid_sphero_ids:
    commands_array.append(Instruction(id, 3, 15))
s.send(pickle.dumps(commands_array))
buffer = s.recv(1024).decode()

commands_array = []
# make spheros green
print("Green")
for id in valid_sphero_ids:
    commands_array.append(Instruction(id, 0, 0, 255, 0))
s.send(pickle.dumps(commands_array))
buffer = s.recv(1024).decode()

'''
commands_array = []
# terminate process
print("Immediate Terminate Test")
for id in valid_sphero_ids:
    commands_array.append(Instruction(id, -2))
s.send(pickle.dumps(commands_array))
buffer = s.recv(1024).decode()
'''