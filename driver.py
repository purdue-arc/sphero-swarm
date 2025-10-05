import pickle
import socket
from algorithms.algorithm import Algorithm
from algorithms.constants import *
from controls.Instruction import Instruction
from spherov2.types import Color


s = socket.socket()
port = 1235

s.connect(('localhost', port))


if __name__ == "__main__":
    sphero_tag = []
    initial_positions = []
    instructions = []
    algorithm = Algorithm(grid_width=GRID_WIDTH,
                            grid_height=GRID_HEIGHT,
                            n_spheros=N_SPHEROS)
    
    # send empty instruction to test communication
    s.send(pickle.dumps(instructions))
    buffer = s.recv(1024).decode()


    running = True
    while running:
        algorithm.update_grid_bonds()
        algorithm.update_grid_move()

        for sphero in algorithm.spheros:
            direction_change = sphero.get_direction_change()

            rotate_instruction = Instruction(sphero_tag[sphero.id - 1], 2, 60 * direction_change, TURN_DURATION)
            instructions.append(rotate_instruction)

            roll_instruction = Instruction(sphero.id, 1, SPHERO_SPEED, ROLL_DURATION)
            instructions.append(roll_instruction)

        # send the instructions
        s.send(pickle.dumps(instructions))

        # waits for a response from the API
        buffer = s.recv(1024).decode()