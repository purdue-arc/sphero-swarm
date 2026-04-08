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
import zmq
from algorithms.form_instruction import nextVectorDirection                                                                                          
from algorithms.constants import ERROR_CORRECTION

def main():
    s = socket.socket()
    port = 1235

    s.connect(('localhost', port))

    # Connect to sphero spotter
    context = zmq.Context()                                                                                                                              
    zmq_socket = context.socket(zmq.REQ)                                                                                                                 
    zmq_socket.connect("tcp://localhost:5555")

    zmq_socket.send_string("init")                                                                                                                       
    response = zmq_socket.recv_string()                                                                                                                  
    print(f"Perception connected: {response}")

    # FIXME What is this, is this deprecated? 
    '''
    call name_to_location = controls.Fall_2025_Sphero_Swarm_Server.generate_dict_map()
    '''

    # sanity checks
    assert len(INITIAL_POSITIONS) == N_SPHEROS, 'Number of initial positions does not match N_SPHEROS'
    assert len(INITIAL_POSITIONS) == len(set(INITIAL_POSITIONS)), 'Cannot have repeats in initial_positions'
    assert len(INITIAL_TRAITS) == N_SPHEROS, 'INITIAL_TRAITS length must match N_SPHEROS'

    # make a list of spheros to pass into algorithm using INITIAL_POSITIONS and INITIAL_TRAITS
    spheros = []
    id = 1
    for (x, y), trait in zip(INITIAL_POSITIONS, INITIAL_TRAITS):
        spheros.append(Sphero(id, x, y, direction=1, trait=trait))
        id += 1


    algorithm = Algorithm(grid_width=GRID_WIDTH,
                            grid_height=GRID_HEIGHT,
                            spheros=spheros)
    print("init success")

    simulation_thread = threading.Thread(target=StartSimulation, args=(algorithm,), daemon=True)
    simulation_thread.start()

    running = True
    try:
        while running:
            print("-"*50)

            # using refactored functions (Spring 26) but testing is needed!
            algorithm.bond_all_groups()
            algorithm.move_all_groups()

            rotate_instructions = []
            roll_instructions = []
            color_instructions = []

            spheros = algorithm.find_all_spheros()
            for sphero in spheros:
                # Set LED to sphero's color (from algorithm: head=RED, tail=BLUE)
                color_instruction = Instruction(sphero.id, 0, sphero.color[0], sphero.color[1], sphero.color[2])
                color_instructions.append(color_instruction)
                # FIXME make get_direction_change work for rotation, 
                # we also may want to rethink how we do this.
                direction_change = sphero.get_direction_change() 

                translation = True
                if translation:
                    # also, make sure controls still wants the id passed in to be 1,2,3... instead of SB-B11D
                    rotate_instruction = Instruction(sphero.id, 2, 45 * direction_change, TURN_DURATION)
                    rotate_instructions.append(rotate_instruction)

                    speed = SPHERO_SPEED

                    # If we are going diagonal, adjust speed by a factor of sqrt(2). thanks pythagoras
                    if sphero.direction > 0 and sphero.direction % 2 == 0:
                        speed = SPHERO_DIAGONAL_SPEED

                    roll_instruction = Instruction(sphero.id, 1, speed, ROLL_DURATION)
                    print(str(sphero))
                    roll_instructions.append(roll_instruction)

                else: # rotation 
                    # TODO implement @Alan @John
                    pass


            # send color instructions first so LEDs update before movement
            s.send(pickle.dumps(color_instructions))
            buffer = s.recv(1024)

            # send rotate instructions
            s.send(pickle.dumps(rotate_instructions))
            buffer = s.recv(1024)

            # send roll instructions
            s.send(pickle.dumps(roll_instructions))

            # waits for a response from the API
            buffer = s.recv(1024)
            
            sleep(4)
            if ERROR_CORRECTION:                                                                                                                                 
                zmq_socket.send_string("coords")                                                                                                                 
                data = zmq_socket.recv_json()                                                                                                                    
                id_to_sphero = {sphero.id: sphero for sphero in algorithm.find_all_spheros()}                                                                    
                for entry in data["spheros"]:                                                                                                                    
                    sphero = id_to_sphero.get(entry["id"])                                                                                                       
                    if sphero:                                                                                                                                   
                        # update real position                                                                                                                   
                        sphero.true_x = entry["x"]                                                                                                                    
                        sphero.true_y = entry["y"]                                                                                                                    
                                                                                                                                                                
                        # distance from real position to target                                                                                                  
                        remaining = math.sqrt((sphero.target_x - sphero.true_x)**2 + (sphero.target_y - sphero.true_y)**2)                                                 
                        dx, dy = position_change[sphero.direction]                                                                                               
                        original = math.sqrt(dx**2 + dy**2)                                                                                                      
                                                                                                                                                                
                        corrected_speed = int(SPHERO_SPEED * (remaining / original)) if original > 0 else 0                                                      
                        corrected_speed = max(0, min(255, corrected_speed))                                                                                      
                                                                                                                                                                
                        angle = nextVectorDirection(                                                                                                             
                            (sphero.true_x, sphero.true_y),                                                                                                                
                            (sphero.target_x, sphero.target_y)                                                                                                   
                        )                                                                                                                                        
                                                                                                                                                                
                        rotate_instruction = Instruction(sphero.id, 2, angle, TURN_DURATION)                                                                     
                        roll_instruction = Instruction(sphero.id, 1, corrected_speed, ROLL_DURATION)                                                             
                                                                                                                                                                
                        s.send(pickle.dumps([rotate_instruction]))                                                                                               
                        s.recv(1024)                                                                                                                             
                        s.send(pickle.dumps([roll_instruction]))                                                                                                 
                        s.recv(1024) 

            # TODO I don't believe this is necessary for the current implementation - we will see
            #for sphero in spheros:
            #    teleport_sphero_to_target(sphero)

    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False
        pygame.quit()
        s.close()

if __name__ == "__main__":
    main()