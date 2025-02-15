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
    
# Field Constants TODO make these accurate to the actual field
WIDTH = 10
HEIGHT = 10

colors = [RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE]

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
#initialize our 3 spheros' positions and directions
# TODO We need to figure out initialization will work.
# But for now, we can just assume that Sphero 0 is at position 0,0 facing direction 5
class Sphero:
    def __init__(self, sphero_id, x, y, target_x, target_y, direction, prev_direction):
        self.id = sphero_id
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.prev_direction = prev_direction 
        self.direction = direction
        self.color = None


if __name__ == "__main__":
    sphero_ids = ["SB-B5A9", "SB-E274", "SB-B11D"]

    # Field object from determine_bind.py. TODO complete initialization after Madhav push
    field = Field()

    instructions = []

    i = 0 # gives the id that is used in the API 
    #TODO We are still working with controls to decide whether we use the actual 
    # sphero id (like "SB-B5A9") or just our own given ids [0, 1, 2, ...]

    for s_id in sphero_ids:
        # get user input for coordinates
        print(f"Input x and y coordinates for sphero {s_id}:")
        x = int(input('x: '))
        y = int(input('y: '))

        # TODO Should we also initialize their direction and target coords here?
        new_sphero = Sphero(s_id, x, y, x, y, -1, -1)

        # give object a color as well as tell the API to give it a color
        new_sphero.color = colors[i % len(colors)]
        instructions.append(Instruction(i, 0, new_sphero.color)) # 0 is change color command

        #TODO use Madhav's method to add this new sphero to the field after he pushes
        status = 0
        # status = field.sphero_pos_init(new_sphero)
        # if status == INVALID:
        #     raise SystemExit(f'invalid coordinates {x},{y} for sphero {s_id}, field initialization failed')
        # if status == SPOT_TAKEN:
        #     raise SystemExit(f'Spot {x},{y} already taken. field initialization failed for sphero {s_id}')

        i += 1

    s.send(pickle.dumps(instructions))
    # waits for a response from the API
    buffer = s.recv(1024).decode()

    # move the ballz
    # while (True):
    #     instructions = [] # empty out instructions every iteration
    #
    #
    #     for sphero_id in range(len(spheros)):
    #         # turn the ball some way
    #         instruction = Instruction(sphero_id, 2, 60 * random.randint(1, 6), TURN_DURATION)
    #         instructions.append(instruction)
    #         # for each of the three balls, randomly choose a new direction
    #
    #     for sphero_id in range(len(spheros)):
    #         instruction = Instruction(sphero_id, 1, SPHERO_SPEED, ROLL_DURATION)
    #         # TODO make sure to avoid collisions
    #         instructions.append(instruction)
    #
    #     # send the instructions
    #
    #     s.send(pickle.dumps(instructions))
    #
    #     # waits for a response from the API
    #     buffer = s.recv(1024).decode()



