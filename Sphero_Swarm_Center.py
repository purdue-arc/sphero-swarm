# still broken - broadcasting kill flag doesn't seem to be working on an interfile basis,
# but otherwise working

import subprocess
import threading
# set up socket and listen for the first broadcasting
import socket
import time

import algorithms.constants
import controls.Fall_2025_Sphero_Swarm_Server
import driver

if __name__ == "__main__":
    global KILL_FLAG

    # Start the producer script as a subprocess
    threads = []
    thread = threading.Thread(target=controls.Fall_2025_Sphero_Swarm_Server.run_server, args=[algorithms.constants.SPHERO_TAGS])
    threads.append(thread)
    thread.start()

    # use socket to kind of tell when the system is ready
    s = socket.socket()
    # arbitrary non-priv port that isn't the one used by the server
    port = 4324
    s.bind(('localhost', port))
    # enables the system to handle 1 connection before refusing more
    s.listen(1)
    print("Waiting for connection to client...")
    # conn is the object required for comm with the other files
    conn, address = s.accept()
    
    thread = threading.Thread(target=driver.main(), args=[algorithms.constants.SPHERO_TAGS])
    threads.append(thread)
    thread.start()

    try:
        while (not all([not thread.is_alive() for thread in threads])):
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Terminating commmands...")
        KILL_FLAG = 1

    for thread in threads:
        thread.join(timeout=None)