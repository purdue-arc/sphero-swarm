import pickle
import socket
from algorithms.algorithm import Algorithm
from algorithms.constants import *
from controls.Instruction import Instruction
from time import sleep
# from spherov2.types import Color




if __name__ == "__main__":
    s = socket.socket()
    port = 1235

    s.connect(('localhost', port))

    #sphero_tag = ["SB-E274", "SB-76B3", "SB-CEB2"]
    sphero_tag = ["SB-E274", "SB-76B3", "SB-CEB2"]
    initial_positions = [(0, 0), (0, 2), (2, 2)]
    algorithm = Algorithm(grid_width=GRID_WIDTH,
                            grid_height=GRID_HEIGHT,
                            n_spheros=3)
    
    # send empty instruction to test communication
    # s.send(pickle.dumps(instructions))
    # buffer = s.recv(1024).decode()
    print("init success")


    running = True
    while running:
        print("new move")
        
        rotate_instructions = []
        roll_instructions = []

        algorithm.update_grid_bonds()
        for sphero in algorithm.spheros: # fix this, I was being lazy
            sphero.x = sphero.target_x
            sphero.y = sphero.target_y
        algorithm.update_grid_move()

        rotate_instructions = []
        roll_instructions = []

        for sphero in algorithm.spheros:
            direction_change = sphero.get_direction_change()
            rotate_instruction = Instruction(sphero.id, 2, 45 * direction_change, TURN_DURATION)
            rotate_instructions.append(rotate_instruction)

            roll_instruction = Instruction(sphero.id, 1, SPHERO_SPEED, ROLL_DURATION)
            roll_instructions.append(roll_instruction)
        
        # send the instructions
        s.send(pickle.dumps(rotate_instructions))

        # waits for a response from the API
        buffer = s.recv(1024)
        print("Buffer:", buffer.split()[0])

        # send the instructions
        s.send(pickle.dumps(roll_instructions))

        # waits for a response from the API
        buffer = s.recv(1024)
        print("Buffer:", buffer.split()[0])