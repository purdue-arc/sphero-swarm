import socket
import time

from Instruction import Instruction
from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import multiprocessing
from threading import Lock
import threading
import pickle
from threading import Barrier
import queue

lock = Lock()

def toy_manager(toy, id, instructions):

    print("start", id)
    print(toy)

    on = True

    with SpheroEduAPI(toy) as api:
        while on:
            if (not instructions.empty()):
                instruction = instructions.get()
                print("new instruction")
                if (instruction.type == 0):
                    print(id, " ", instruction.color)
                    print("start")
                    api.set_main_led(instruction.color)
                    api.set_back_led(instruction.color)
                    api.set_front_led(instruction.color)
                    print("end")
                elif (instruction.type == 1): # roll
                    api.roll(api.get_heading(), instruction.speed, instruction.duration)
                elif (instruction.type == 2): # turn
                    api.spin(instruction.degrees, instruction.duration)
                elif (instruction.type == 4): # stop
                    on = False
                    break

                barrier.wait()
            # end if
        # end while
    # end with
    print("end")
# end toy_manager

def controls(instructions):

    s = socket.socket()
    port = 12345

    s.bind(('localhost', port))

    s.listen(5)

    print("Waiting for connection")

    c, address= s.accept()

    on = True

    while (on):
        instructionList = pickle.loads(c.recv(1024))

        try:
            lock.acquire()
            for instruction in instructionList:
                print(instruction.type)
                if (instruction.type == 0):
                    print(instruction.spheroID)
                    print(instruction.color)
                elif (instruction.type == 1):
                    print(instruction.spheroID)
                    print(instruction.speed)
                    print(instruction.duration)
                elif (instruction.type == 2):
                    print(instruction.spheroID)
                    print(instruction.degrees)
                    print(instruction.duration)
                elif (instruction.type == 3):
                    on = False

                if (not (instruction.spheroID < len(instructions))):
                    print("index out of bounds")
                else :
                    instructions[instruction.spheroID].put(instruction)
        finally:
            lock.release()
            # end try

        barrier.wait() # wait for all instructions to finish

        print("Done")
        c.send("Done".encode())
        print("Message Sent")

        # end for
    # end while
# end controls()

def run_toy_threads(toys, instructions):
    id = 0
    threads = []

    for toy in toys:
        print("adding", id)
        thread = threading.Thread(target=toy_manager, args=[toy, id, instructions[id]], daemon = True)
        threads.append(thread)
        thread.start()
        id += 1

    thread = threading.Thread(target=controls, args=[instructions], daemon = True)
    thread.daemon = True
    threads.append(thread)
    thread.start()

    for thread in threads:

        thread.join()

    print("Ending function...")
# end run_toy_threads()

# start main

toys = scanner.find_toys(toy_names = ["SB-B5A9", "SB-E274"])
"""
try:
    for toy in toys:  # fighting back against the bleak error exceptions
        with SpheroEduAPI(toy) as api:
            # api.calibrate_compass()
            api.reset_aim()
except:
    print("Error!")
    sys.exit()
"""

print(len(toys))
barrier = Barrier(len(toys) + 1)

instructions = [multiprocessing.Queue() for i in range(len(toys))]

run_toy_threads(toys, instructions)

