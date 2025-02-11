import pickle
import socket
from controls.Instruction import Instruction
from spherov2.types import Color

from determine_bind import Field

s = socket.socket()
port = 1234

s.connect(('localhost', port))

# Example instruction:
# change color of sphero 1 to (114, 186, 133)
Instruction(1, 0, Color(114, 186, 133)) 

#initialize our 3 spheros' positions and directions
# TODO We need to figure out initialization will work.
# But for now, we can just assume that Sphero 0 is at position 0,0 facing direction 5
class Sphero:
    def __init__(self, x, y, target_x, target_y, direction, prev_direction):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.prev_direction = prev_direction 
        self.direction = direction


spheros = []

# instantiate 3 spheros

while (True):
    instructions = []
    # move the balls

    for sphero_id in range(len(spheros)):
        instruction = Instruction(1, 0, Color(114, 186, 133)) 
        instructions.append(instruction)
        # for each of the three balls, randomly choose a new direction
        instructions.append(instruction)
        # make sure to avoid collisions

    # send the instructions

    s.send(pickle.dumps(instructions))



