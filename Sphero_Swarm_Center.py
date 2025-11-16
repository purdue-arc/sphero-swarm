# ongoing work - please do not change it - for the love of all that is decent and working
# still broken - broadcasting kill flag doesn't seem to be working on an interfile basis

import subprocess
import threading
# set up socket and listen for the first broadcasting
import socket
import time

import algorithms 
import controls.Fall_2025_Sphero_Swarm_Server

if __name__ == "__main__":
    global KILL_FLAG
    # Start the producer script as a subprocess
    threads = []
    thread = threading.Thread(target=controls.Fall_2025_Sphero_Swarm_Server.test_controls, args=[])
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