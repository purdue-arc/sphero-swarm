import pickle
import socket
import random 
from controls.Instruction import Instruction
from spherov2.types import Color

from determine_bind import Field

s = socket.socket()
port = 1234

s.connect(('localhost', port))

# Example instruction:
# change color of sphero 1 to (114, 186, 133)
Instruction(1, 0, Color(114, 186, 133)) 

BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

# CONSTANTS TODO make em right
SPHERO_SPEED = 1
ROLL_DURATION = 1
TURN_DURATION = 1

colors = [RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE]

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
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


spheros = ["SB-B5A9", "SB-E274", "SB-B11D"]

# instantiate 3 spheros' colors
instructions = []
for sphero_id in range(len(spheros)):
    # 0 is change color command
    instruction = Instruction(sphero_id, 0, colors[sphero_id % len(colors)]) 
    instructions.append(instruction)

s.send(pickle.dumps(instructions))
# waits for a response from the API
buffer = s.recv(1024).decode()

while (True):
    # move the ballz
    instructions = []

    for sphero_id in range(len(spheros)):

        # turn the ball some way
        instruction = Instruction(sphero_id, 2, 60 * random.randint(1, 6), TURN_DURATION)
        instructions.append(instruction)
        # for each of the three balls, randomly choose a new direction

    for sphero_id in range(len(spheros)):
        instruction = Instruction(sphero_id, 1, SPHERO_SPEED, ROLL_DURATION)
        # TODO make sure to avoid collisions
        instructions.append(instruction)

    # send the instructions

    s.send(pickle.dumps(instructions))

    # waits for a response from the API
    buffer = s.recv(1024).decode()



