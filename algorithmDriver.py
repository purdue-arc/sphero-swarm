import pickle # to unbytedump our stuff
import zmq # for socket to connect to algs
import random
from controls.Instruction import Instruction
from spherov2.types import Color
import math
import time
import socket as controlsSocket
from algorithms.formInstruction import nextVectorDirection, nextVectorMagnitude

# Color constants
BLUE = Color(0, 0, 255)
RED = Color(255, 0, 0)
GREEN = Color(0, 255, 0)
YELLOW = Color(255, 255, 0)
PURPLE = Color(128, 0, 128)
ORANGE = Color(255, 165, 0)

# CONSTANTS 
SPHERO_SPEED = 60
ROLL_DURATION = 1 # in seconds
TURN_DURATION = 1 # in seconds

if __name__ == '__main__':

    # set up client for controls
    s = controlsSocket.socket()
    port = 1235

    s.connect(('localhost', port))

    # set up client 
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    print('socket connected')

    # check connection to the sphero_spotter
    socket.send_string("init")
    print('init')
    msg = socket.recv_string()
    print(msg)
    if msg != 'connected':
        print('something went wrong')
        exit()

    print('Client: Asking perceptions for coords')
    # pretend this is your driver loop. This example will ask for coordinates 
    # N_LOOPS loops number of times. 
    while True:

        '''

        Algorithm calculates next positions here
        
        '''

        spheros_next_coords = [] # An array of where every sphero wants to go next

        instructions = [] # The array of instructions we will eventually send controls
        for sphero in spheros_next_coords:
            socket.send_string(sphero.id)
            print("Sent request to get real coords of sphero {}", sphero.id)
            response = socket.recv_json()
            print("Sphero {} is actually at position ({}, {})", response)
            direction = nextVectorDirection({response.x - sphero.prev_x, response.y - sphero.prev_y}, {sphero.target_x, sphero.target_y})
            magnitude = nextVectorMagnitude({response.x, response.y}, {sphero.x, sphero.y})
            instructions.append(Instruction(sphero.id, 2, direction, TURN_DURATION))
            instructions.append(Instruction(sphero.id, 1, magnitude, ROLL_DURATION))

            '''
            Update coordinates:

            1. Now that we know the actual coords of a sphero, we set the previous to this value
            2. For now, we set the current coordinate of the spheoro to the expected coords that
            the algorithm wants our sphero to go to. In the next iteration, we will find the actual
            coordinates the sphero went to and update the next prev accordingly
            '''
            sphero.prev_x = response.x
            sphero.prev_y = response.y
            sphero.x = sphero.target_x
            sphero.y = sphero.yarget_y

        quit = True
        s.send(pickle.dumps(instructions))
        buffer = s.recv(1024).decode()


        if quit:
            break
    
    # tell sphero_spotter listener to exit
    socket.send_string('exit')