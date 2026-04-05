import pickle
import socket
import math
from algorithms.algorithm import Algorithm
from algorithms.constants import *
from algorithms.simulation import StartSimulation, spheros, teleport_sphero_to_target
from algorithms.sphero import Sphero
from controls.Instruction import Instruction
from time import sleep
import threading
import pygame

def main():
    algorithm.log('STARTING CALIBRATION DRIVER')
    s = socket.socket()
    port = 1235

    s.connect(('localhost', port))

    # sanity checks
    assert len(INITIAL_POSITIONS) == N_SPHEROS, 'Number of initial positions does not match N_SPHEROS'
    assert len(INITIAL_POSITIONS) == len(set(INITIAL_POSITIONS)), 'Cannot have repeats in initial_positions'

    # generate random colors for spheros. FIXME NOT SURE IF THIS IS USED/NECESSARY
    colors = []
    for i in range(N_SPHEROS):
        colors.append(COLORS[i % len(COLORS)])

    # make a list of spheros to pass into algorithm using constant INITIAL_POSITIONS
    spheros = []
    id = 1
    for x, y in INITIAL_POSITIONS:
        spheros.append(Sphero(id, x, y, direction=1)) # initialize spheros to be pointing to direction positive y
        id += 1


    algorithm = Algorithm(grid_width=GRID_WIDTH,
                            grid_height=GRID_HEIGHT,
                            spheros=spheros)
    algorithm.log("init success")

    simulation_thread = threading.Thread(target=StartSimulation, args=(algorithm,), daemon=True)
    simulation_thread.start()

    running = True
    try:
        if running:
            algorithm.log('Starting calibration')

            # using refactored functions (Spring 26) but testing is needed!
            algorithm.bond_all_groups()
            algorithm.move_all_groups()

            rotate_instructions = []
            roll_instructions = []

            spheros = algorithm.find_all_spheros()
            for sphero in spheros:    

                speed = SPHERO_SPEED

                roll_instruction = Instruction(sphero.id, 1, speed, ROLL_DURATION)
                algorithm.log(str(sphero))
                roll_instructions.append(roll_instruction)

                algorithm.log(f'Sphero {sphero.id} moving')

            # send the instructions
            s.send(pickle.dumps(roll_instructions))
            algorithm.log('Sending instructions')

            # waits for a response from the API
            buffer = s.recv(1024)
            algorithm.log('Response recieved')

    except KeyboardInterrupt:
        algorithm.log("\nShutting down...")
        running = False
        pygame.quit()
        s.close()

    algorithm.log('Calibration complete')

if __name__ == "__main__":
    main()