import zmq
import threading








# @Prithika @Anthony
# - Coordinate class
#       Sphero ID
#       x coord
#       y coord



# @Prithika - create function that takes pixel coords and spits out grid coords. 
grid_dimensions = [10, 12]
frame_dim_x = 12316
frame_dim_y = 1440
# 

def get_sphero_coords():
    '''
    Returns list of coords of all spheros in terms of grid units.
    '''
    return 'TODO'

def listener():
    # connect to the socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")

    print("sphero_spotter connected! yippee")

    socket.send_string("sphero_spotter.py connected! yippee!!!!")

thread = threading.Thread(target=listener, daemon=True)
thread.start()


if __name__ == '__main__':
    # initialize some stuff



    # listening loop 
    while True:
        # algorithms will send "1"
        message = socket.recv_string()
        print(f"Received request from algorithms! ima send back info now")

        #reply = f"Response to {message}"
        sphero_coords = get_sphero_coords()

        socket.send_string(sphero_coords)



