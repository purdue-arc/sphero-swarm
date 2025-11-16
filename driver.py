import pickle
import socket
import math
from algorithms.algorithm import Algorithm
from algorithms.constants import *
from algorithms.simulation import StartSimulation, spheros, teleport_sphero_to_target
from controls.Instruction import Instruction
from time import sleep
import threading
import pygame

if __name__ == "__main__":
    s = socket.socket()
    port = 1235

    s.connect(('localhost', port))

    sphero_tag = SPHERO_TAGS
    initial_positions = INITIAL_POSITIONS

    '''
    call name_to_location = controls.Fall_2025_Sphero_Swarm_Server.generate_dict_map()
    '''

    algorithm = Algorithm(grid_width=GRID_WIDTH,
                            grid_height=GRID_HEIGHT,
                            n_spheros=len(sphero_tag),
                            initial_positions=initial_positions)
    print("init success")

    simulation_thread = threading.Thread(target=StartSimulation, args=(algorithm,), daemon=True)
    simulation_thread.start()

    running = True
    try:
        while running:
            print("-"*50)

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

                speed = SPHERO_SPEED

                # If we are going diagonal, adjust speed by a factor of sqrt(2). thanks pythagoras
                if sphero.direction > 0 and sphero.direction % 2 == 0:
                    speed = SPHERO_DIAGONAL_SPEED

                roll_instruction = Instruction(sphero.id, 1, speed, ROLL_DURATION)
                print(str(sphero))
                roll_instructions.append(roll_instruction)


            # send the instructions
            s.send(pickle.dumps(rotate_instructions))

            # waits for a response from the API
            buffer = s.recv(1024)

            # send the instructions
            s.send(pickle.dumps(roll_instructions))

            # waits for a response from the API
            buffer = s.recv(1024)
            
            sleep(4)
    
            for sphero in spheros:
                teleport_sphero_to_target(sphero)

    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False
        pygame.quit()
        s.close()