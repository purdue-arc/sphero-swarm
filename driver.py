import pickle
import socket
from algorithms.algorithm import Algorithm
from algorithms.constants import *
from controls.Instruction import Instruction
from time import sleep


if __name__ == "__main__":
    s = socket.socket()
    port = 1235

    s.connect(('localhost', port))

    sphero_tag = SPHERO_TAGS
    initial_positions = [(0,0), (2,0), (4,0), (6, 0)]

    algorithm = Algorithm(grid_width=GRID_WIDTH,
                            grid_height=GRID_HEIGHT,
                            n_spheros=len(sphero_tag),
                            initial_positions=initial_positions)
    print("init success")


    running = True
    while running:
        rotate_instructions = []
        roll_instructions = []

        for sphero in algorithm.spheros:
            sphero.x = sphero.target_x
            sphero.y = sphero.target_y
        algorithm.update_grid_bonds()
        algorithm.update_grid_move()

        rotate_instructions = []
        roll_instructions = []

        for sphero in algorithm.spheros:
            direction_change = sphero.get_direction_change()
            rotate_instruction = Instruction(sphero.id, 2, 45 * direction_change, TURN_DURATION)
            rotate_instructions.append(rotate_instruction)

            roll_instruction = Instruction(sphero.id, 1, SPHERO_SPEED, ROLL_DURATION)
            print(str(sphero))
            roll_instructions.append(roll_instruction)

        #sleep(1)

        # send the instructions
        s.send(pickle.dumps(rotate_instructions))

        # waits for a response from the API
        buffer = s.recv(1024)

        # send the instructions
        s.send(pickle.dumps(roll_instructions))

        # waits for a response from the API
        buffer = s.recv(1024)