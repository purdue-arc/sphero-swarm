import threading 
import pickle
import zmq # for socket to connect to algs
import time

from SpheroCoordinate import SpheroCoordinate

# CONSTANTS
GRID_DIM_X = 12 # TODO actually like make these real. right now they are all made up 
GRID_DIM_Y = 10
frame_dim_x = 1080
frame_dim_y = 1440

# Global array of SpheroCoordinates
spheros = []

def pixel_to_grid_coords(pixel_x, pixel_y):
    '''
    TODO 
    @Prithika - create function that takes pixel coords and spits out grid coords based off of our grid size.
    '''
    pass
    return None
# 

def initialize_spheros():
    '''
    TODO @anthony
    initializes global sphero object array.
    Returns number of spheros found.
    '''
    n_found = 0
    return n_found

# Define a global stop event
stop_event = threading.Event()

def listener():
    '''
    This function is started in a thread and concurrently listens for requests from Algorithm team's side.

    Algorithm team will send a request containing "init" and we will wait for that. we will send back a message saying 
    "connected" and then start listening for strings saying "coords". When we receive a string 
    containing "exit", the listener will stop.
    '''
    # connect to the socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    print('sphero_spotter: socket bind success')


    # start listening for 'init', 'coords' requests or 'exit'.
    while not stop_event.is_set():
        print('sphero_spotter: listening...')
        msg = socket.recv_string()
        print(f"Received request '{msg}' from algorithms!")

        if msg == 'init':
            num_found = initialize_spheros() # get their positions and assign IDs.
            socket.send_string(f"connected to {num_found} spheros")

        elif msg == 'coords':
            #reply = pickle.dump(get_sphero_coords())    # byte dump list of spheros. Algorithms gets to unpack it
            #reply = pickle.dump('hi')
            #socket.send(reply)                   # send bytedump of sphero coord objects back
            socket.send_string('[pickled SpheroCoordinate objects]')
            print('sphero_spotter: sending coords')

        elif msg == 'exit':
            socket.send_string('bye')
            break

        else:
            socket.send_string("error - command doesn\'t match one of ['init', 'coords', 'exit']")




if __name__ == '__main__':

    # start the listening thread
    thread = threading.Thread(target=listener, daemon=False) # start a listening thread
    # we do daemon=False because if the listener is shut down then we want the 
    # spotter to close.
    thread.start()

    # TODO start the camera feed, object tracking and updating, all that stuff







