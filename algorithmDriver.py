import pickle # to unbytedump our stuff
import zmq # for socket to connect to algs

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

    print('Client: Asking perceptions for coords')
    # pretend this is your driver loop. This example will ask for coordinates 
    # N_LOOPS loops number of times. 
    while True:

        '''

        Algorithm calculates next positions here
        
        '''

        spheros_next_coords = [] # An array of where every sphero wants to go next

        for sphero in spheros_next_coords:
            socket.send_string(sphero.id)
            print("Sent request to get real coords of sphero ")
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