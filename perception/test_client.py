'''
Hello algorithms team! Here is an example client that shows how to
interface with our sphero_spotter.py program. 

First run the sphero_spotter.py, then run your driver code / client.
'''

import pickle # to unbytedump our stuff
import zmq # for socket to connect to algs

import time # simulate the driver running. you don't need this

if __name__ == '__main__':

    # set up zmq socket
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

    '''
    now you are connected, and you can query the coordinates by sending
    'coords' through the socket. This will return a pickle dump of Sphero coordinate objects,
    which can be found in [INSERT WHEN WE MAKE THAT CLASS]. follow our example for unwrapping it.
    '''


    '''
    '''

    N_LOOPS = 10
    count = 0

    print('Client: Asking for coords')
    # pretend this is your driver loop. This example will ask for coordinates 
    # N_LOOPS loops number of times. 
    while count < N_LOOPS:
        count += 1
        time.sleep(1) # pretend to wait for spheros to move 

        # send a request to sphero_spotter for coordinates.
        request = 'coords'
        print("Sent:\t\t", request)
        socket.send_string(request)

        # receive a bytedump of SpheroCoordinate objects and unpickle it. 
        # TODO look at controls code for unpickling 
        # maybe do recv_multipart() and send_multipart()? look into it.
        #bytedump = pickle.loads(socket.recv())
        #print(bytedump)

        response = socket.recv_string()
        print("Received:\t", response)
    
    # tell sphero_spotter listener to exit
    socket.send_string('exit')