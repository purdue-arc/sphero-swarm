import pickle
import socket
import random
from Instruction import Instruction
from spherov2.types import Color
import math

from determine_bind import Field

s = socket.socket()
port = 1235

s.connect(('localhost', port))

# Color constants
BLUE = Color(0, 0, 255)
RED = Color(255, 0, 0)
GREEN = Color(0, 255, 0)
YELLOW = Color(255, 255, 0)
PURPLE = Color(128, 0, 128)
ORANGE = Color(255, 165, 0)

# CONSTANTS 
SPHERO_SPEED = 90
ROLL_DURATION = 0.5 # in seconds
TURN_DURATION = 1 # in seconds
    
# Field Constants TODO make these accurate to the actual field
WIDTH = 10
HEIGHT = 10

colors = [RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE]

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

    def check_bonding(self, other):
        x_distance = abs(self.x - other.x)
        y_distance = abs(self.y - other.y)

        # squished the grid, do not want a vertical bond
        # x_distance must be with 0 to 2, y_distance must be within 0 to 1
        if (x_distance < 3 and y_distance < 2):
            return True
        return False

    def update_self_direction(self, direction_change):
        '''
        direction_change = 0: don't change direction
        direction_change = 1: turn left 60 degrees
        direction_change = -1: turn right 60 degrees
        '''
        self.prev_direction = self.direction
        self.direction = (self.direction + direction_change)

        #direction values should be 1 through 6, make sure it doesnt go over or under range
        if (self.direction > 6):
            self.direction = 1

        if self.direction < 1:
            self.direction = 6

    def get_direction_change(prev_direction, next_direction):
        '''
        given the prev and next direction, returns the direction change.

        used for the API calls, which take an amount of rotation in degrees
        '''
        #TODO make direction change the most optimal direction
        # for example going from direction 1 to direction 6 should be a turn of -1
        direction_change = next_direction - prev_direction
        return direction_change


    def get_target(self):
        '''
        returns a new target_x, target_y based on direction
        '''
        if (self.direction == 1):
            return (self.x + 2, self.y)

        # move up right
        elif (self.direction == 2):
            return (self.x + 1, self.y - 1)

        # move up left
        elif (self.direction == 3):
            return (self.x - 1, self.y - 1)

        # move left
        elif (self.direction == 4):
            return (self.x - 2, self.y)

        # move down left
        elif (self.direction == 5):
            return (self.x - 1, self.y + 1)

        # move down right
        elif (self.direction == 6):
            return (self.x + 1, self.y + 1)



if __name__ == "__main__":
    #sphero_ids = ["SB-B5A9", "SB-E274", "SB-B11D"]

    field = Field(WIDTH, HEIGHT)

    instructions = []
    spheros = []

    N = 1 # number of spheros

    for sphero_id in range(N):
        # get user input for coordinates
        field.print_array()
        print()
        print(f"Input x and y coordinates for sphero {sphero_id}:")
        x = int(input('x: '))
        y = int(input('y: '))

        # initialize their direction to 0 degrees (direction 1)
        new_sphero = Sphero(sphero_id, x, y, x, y, 1, 1)

        spheros.append(new_sphero)

        # give object a color as well as tell the API to give it a color
        new_sphero.color = colors[sphero_id % len(colors)]
        instructions.append(Instruction(sphero_id, 0, new_sphero.color)) # 0 is change color command

        status = field.sphero_pos_init(new_sphero)
        if status == Field.INVALID:
            raise SystemExit(f'invalid coordinates {x},{y} for sphero {sphero_id}, field initialization failed')
        if status == Field.SPOT_TAKEN:
            raise SystemExit(f'Spot {x},{y} already taken. field initialization failed for sphero {sphero_id}')


    field.initialize_spheros(spheros)

    s.send(pickle.dumps(instructions))
    # waits for a response from the API
    buffer = s.recv(1024).decode()




    # move the spheros
    while (True):
        instructions = [] # empty out instructions every iteration

        # reset the next_field array before
        field.reset_next_field()

        # create bonds
        bonds = field.group_sphero_objects(spheros)

        # The below code to update direction was taken from 
        # Siddh Saxena of the Sphero Swarm Algorithms Team Hall of Fame

        # i goes through each bonding group
        for i in range(len(bonds)):

            # generate new direction (patent pending)
            direction = random.randint(1, 6)

            print("initial chosen direction, line 175:",direction)

            # update the spheros in the bonding groups direction and target
            # j goes through each sphero in the selected bonding group
            for j in range(len(bonds[i])):
                sphero = bonds[i][j]
                sphero.direction = direction
                sphero.target_x, sphero.target_y = sphero.get_target()

                print(f"current position {sphero.x} {sphero.y}, updated target, line 184, {sphero.target_x} {sphero.target_y}")
                #sphero.update_direction(direction)
                #sphero.update_target()

            # IDEA:
            #   check all other previous bonding group's spheros target_x and target_y with our own sphero's target_x and target_y
            #   if there is a potential collision that means the direction we had previously chosen is invalid, thus remove it from
            #   the list of available directions. Once we have gone through all spheros and checked if they will collide with a previous
            #   sphero we simply choose a direction from the remaining list and reupdate the all of the sphero's directions in the bonding group
            
            #   If absolutely no available direction exists then just stay in place for this cycle

            # CODE:
            available_directions = [1, 2, 3, 4, 5, 6] # list of possible movement direction
            current_direction = direction - 1 # index of the current direction
            collision = False # collision flag

            # Iterate through all spheros in the current bond group
            for j in range(len(bonds[i])):

                sphero = bonds[i][j]
                #sphero.update_direction(available_directions[current_direction])
                #Jsphero.update_target()
                if len(available_directions) != 0:
                    sphero.direction = available_directions[current_direction]
                    sphero.target_x, sphero.target_y = sphero.get_target()
                else:
                    sphero.target_x, sphero.target_y = sphero.x, sphero.y

                # check out of bounds for first bonding group
                if (i == 0):
                    found_direction = False
                    while (found_direction == False):

                        # if any sphero is out of bounds find a new direction
                        error = False
                        if (sphero.target_x < 0 or sphero.target_x > WIDTH):
                            error = True
                        if (sphero.target_y < 0 or sphero.target_y > HEIGHT):
                            error = True
                        
                        if (error == True):
                            print(f"out of bounds error is detected, line 226 {sphero.target_x} {sphero.target_y}, out of bounds is 0 and {WIDTH} & {HEIGHT}")
                            if (len(available_directions) != 0):
                                collision = True
                                # this direction doesn't work, so remove it
                                available_directions.pop(current_direction)

                                # since removing we are shifting the list, we need to adjust the current direction
                                if (current_direction >= len(available_directions)):
                                    current_direction = 0
                                
                                if (len(available_directions) != 0):
                                    sphero.direction = available_directions[current_direction]
                                    print(f'j = {j}, current_direction while finding avaialble direction line 235 = {available_directions[current_direction]}')
                                    sphero.target_x, sphero.target_y = sphero.get_target()
                                    print(f"line 240 new target {sphero.target_x} {sphero.target_y}")
                                else:
                                    print("no more available directions, line 238")
                                    sphero.target_x, sphero.target_y = sphero.x, sphero.y
                            else:    
                                #don't move
                                sphero.target_x, sphero.target_y = sphero.x, sphero.y
                            #sphero.update_direction(available_directions[current_direction])
                            #sphero.update_target()

                        else:
                            found_direction = True

                #check all previous bonding groups for potential collisions
                for k in range(i):
                    for l in range(len(bonds[k])):
                        other = bonds[k][l]

                        found_direction = False
                        while (found_direction == False):

                            # if two spheros' x and y coordinates are close enough to each other (not exactly the same, but within a threshhold) 
                            # or if they are out of bounds then change the direction
                            error = False
                            if (abs(other.target_x - sphero.target_x) == 0 and abs(other.target_y - sphero.target_y) == 0):
                                error = True
                            if (sphero.target_x < 0 or sphero.target_x > WIDTH):
                                error = True
                            if (sphero.target_y < 0 or sphero.target_y > HEIGHT):
                                error = True
                            
                            if (error == True):
                                collision = True
                                if (len(available_directions) != 0):
                                    # this direction doesn't work, so remove it
                                    available_directions.pop(current_direction)

                                    # since removing we are shifting the list, we need to adjust the current direction
                                    if (current_direction >= len(available_directions)):
                                        current_direction = 0

                                    if (len(available_directions) != 0):
                                        print(f'j = {j}, current_direction while finding avaialble direction line 279 = {available_directions[current_direction]}')
                                        sphero.direction = available_directions[current_direction]
                                        sphero.target_x, sphero.target_y = sphero.get_target()
                                    else:
                                        print("no available directions line 282")
                                        sphero.target_x, sphero.target_y = sphero.x, sphero.y
                                else:
                                    sphero.target_x, sphero.target_y = sphero.x, sphero.y
                                #sphero.update_direction(available_directions[current_direction])
                                #sphero.update_target()
                            else:
                                found_direction = True
                
                    # reupdate all spheros to make sure they are all moving the same direction
                    if (collision == True):
                        # go through all the spheros in the bonding group and update their direction
                        for j in range(len(bonds[i])):
                            sphero = bonds[i][j]
                    
                            if (len(available_directions) != 0):

                                print(f'j = {j}, current_direction while finding avaialble direction line 299 = {available_directions[current_direction]}')
                                #sphero.update_direction(available_directions[current_direction])
                                sphero.direction = available_directions[current_direction]
                                sphero.target_x, sphero.target_y = sphero.get_target()
                                #sphero.update_target()
                                
                            # if no available directions exist, then just stop moving
                            else:
                                print('no available directions exist!')
                                sphero.target_x, sphero.target_y = sphero.x, sphero.y
      

        for sphero in spheros:
            direction_change = Sphero.get_direction_change(sphero.prev_direction, sphero.direction)
            print("direction change line 313", direction_change) 
            sphero.prev_direction = sphero.direction
            instruction = Instruction(sphero.id, 2, direction_change, TURN_DURATION)
            instructions.append(instruction)

            sphero.x, sphero.y = sphero.target_x, sphero.target_y
            
        # All bonding & turning is finished by this point.
        # Now tell spheros to roll forward one unit.
        for sphero in spheros:
            instruction = Instruction(sphero.id, 1, SPHERO_SPEED, ROLL_DURATION)
            instructions.append(instruction)

        # send the instructions
        s.send(pickle.dumps(instructions))

        # waits for a response from the API
        buffer = s.recv(1024).decode()



