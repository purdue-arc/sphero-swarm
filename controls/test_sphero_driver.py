# 3/2/2025
# USING COMMIT ce27ee3123b701e1b444b6fabd180785266d3469
# used for testing, version without bonding implemented.
# TODO DON'T USE

import pickle
import socket
import random
from Instruction import Instruction
from spherov2.types import Color

from determine_bind import Field

s = socket.socket()
port = 1235
s.connect(('localhost', port))

# Example instruction:
# change color of sphero 1 to (114, 186, 133)
# Instruction(1, 0, Color(114, 186, 133)) 

BLUE = Color(0, 0, 255)
RED = Color(255, 0, 0)
GREEN = Color(0, 255, 0)
YELLOW = Color(255, 255, 0)
PURPLE = Color(128, 0, 128)
ORANGE = Color(255, 165, 0)

# CONSTANTS 
SPHERO_SPEED = 90
ROLL_DURATION = 0.5
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
# But for now, we can just assume that each Sphero is at position 0,0 facing direction 1
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

    def update_self_direction(self, direction_change):
        '''
        direction_change = 0: don't change direction
        direction_change = 1: turn left 60 degrees
        direction_change = -1: turn right 60 degrees
        '''
        self.prev_direction = self.direction
        self.direction = (self.direction + direction_change) % 6
        if self.direction == 0:
            self.direction = 6

    def get_target(self):
        '''
        returns a new target_x, target_y based on direction
        '''
        if (self.direction == 1):
            return (self.target_x + 2, self.target_y)

        # move up right
        elif (self.direction == 2):
            return (self.target_x + 1, self.target_y + 1)

        # move up left
        elif (self.direction == 3):
            return (self.target_x - 1, self.target_y + 1)

        # move left
        elif (self.direction == 4):
            return (self.target_x - 2, self.target_y)

        # move down left
        elif (self.direction == 5):
            return (self.target_x - 1, self.target_y - 1)

        # move down right
        elif (self.direction == 6):
            return (self.target_x + 1, self.target_y - 1)



if __name__ == "__main__":
    #sphero_ids = ["SB-B5A9", "SB-E274", "SB-B11D"]

    # Field object from determine_bind.py. TODO complete initialization after Madhav push
    field = Field(WIDTH, HEIGHT)

    field.print_array()

    instructions = []
    spheros = []

    N = 3
    for sphero_id in range(N):
        # get user input for coordinates
        print(f"Input x and y coordinates for sphero {sphero_id}:")
        x = int(input('x: '))
        y = int(input('y: '))

        # initialize their direction to 0 degrees (direction 1)
        new_sphero = Sphero(sphero_id, x, y, x, y, 1, 1)

        spheros.append(new_sphero)

        # give object a color as well as tell the API to give it a color
        new_sphero.color = colors[sphero_id % len(colors)]
        instructions.append(Instruction(sphero_id, 0, new_sphero.color)) # 0 is change color command

        #TODO use Madhav's method to add this new sphero to the field after he pushes
        status = field.sphero_pos_init(new_sphero)
        if status == Field.INVALID:
            raise SystemExit(f'invalid coordinates {x},{y} for sphero {sphero_id}, field initialization failed')
        if status == Field.SPOT_TAKEN:
            raise SystemExit(f'Spot {x},{y} already taken. field initialization failed for sphero {sphero_id}')


    field.initialize_spheros(spheros)

    s.send(pickle.dumps(instructions))
    # waits for a response from the API
    buffer = s.recv(1024).decode()

    # move the ballz
    while (True):
        instructions = [] # empty out instructions every iteration

        #reset the next_field array
        field.reset_next_field()

        for sphero in spheros:

            # turn the ball some direction
            invalid = True
            new_x, new_y, direction_change = 0, 0, 0
            # valid next move check
            while invalid:
                # pick a valid direction change from [-1, 0, 1]
                direction_change = random.randint(-1, 1)

                #update the direction in the sphero
                sphero.update_self_direction(direction_change)
                
                # check if valid
                new_x, new_y = sphero.get_target()

                #if it's valid break out of the loop
                if field.sphero_pos_init_next(sphero, new_x, new_y) == Field.OK:
                    invalid = False

            # now we broke out of the validity checking loop
            # so let's update the sphero target!
            sphero.x = sphero.target_x
            sphero.y = sphero.target_y
            sphero.target_x = new_x
            sphero.target_y = new_y
            sphero.prev_direction = sphero.direction
            # so let's send the instruction :)
            instruction = Instruction(sphero.id, 2, 60 * direction_change, TURN_DURATION)
            instructions.append(instruction)


        # tell the sphero to roll forward
        for sphero in spheros:
            instruction = Instruction(sphero.id, 1, SPHERO_SPEED, ROLL_DURATION)
            instructions.append(instruction)


        # send the instructions
        s.send(pickle.dumps(instructions))

        # waits for a response from the API
        buffer = s.recv(1024).decode()




