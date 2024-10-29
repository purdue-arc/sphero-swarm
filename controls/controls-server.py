import socket
from Instruction import Instruction
from spherov2 import scanner # turning works on relative direction, need to update code to match
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import multiprocessing
from threading import Lock
import threading
import time
import sys
import pickle
import queue

lock = Lock()

def toy_manager(toy, id, instructions):
    print("start", id)
    print(toy)

    with SpheroEduAPI(toy) as api:
        while True:
            if (not instructions.empty()):
                #try:
                    #lock.acquire()
                    instruction = instructions.get()
                    print("new instruction")
                    if (instruction.type == 0):
                        # insert command to reset yaw
                        print("reset yaw")
                    elif (instruction.type == 1):
                        # insert command to reset locator
                        print("reset locator")
                    elif (instruction.type == 2):
                        print(id, " ", instruction.color)
                        print("start")
                        api.set_main_led(instruction.color)
                        api.set_back_led(instruction.color)
                        api.set_front_led(instruction.color)
                        print("end")
                    elif (instruction.type == 3):
                        api.roll(instruction.heading, instruction.speed, instruction.duration)
                #finally:
                    #lock.release()
                # end try
            # end if
        # end while
    # end with
# end toy_manager

def controls(instructions):

    s = socket.socket()
    port = 12345

    s.bind(('localhost', port))

    s.listen(5)

    print("Waiting for connection")

    c, address = s.accept()

    while (True):
        instructionList = pickle.loads(c.recv(1024))

        try:
            lock.acquire()
            for instruction in instructionList:
                print(instruction.type)
                if (instruction.type == 2):
                    print(instruction.spheroID)
                    print(instruction.color)
                elif (instruction.type == 3):
                    print(instruction.spheroID)
                    print(instruction.heading)
                    print(instruction.speed)
                    print(instruction.duration)

                if (not (instruction.spheroID < instructions.len)):
                    print("index out of bounds")
                else :
                    instructions[instruction.spheroID].put(instruction)
        finally:
            lock.release()
            # end try
        # end for
    # end while
# end controls()

def run_toy_threads(toys, instructions):
    id = 0
    threads = []

    for toy in toys:
        print("adding", id)
        thread = threading.Thread(target=toy_manager, args=[toy, id, instructions[id]])
        threads.append(thread)
        thread.start()
        id += 1

    thread = threading.Thread(target=controls, args=[instructions])
    threads.append(thread)
    thread.start()

    for thread in threads:
        thread.join()

    print("Ending function...")
# end run_toy_threads()

# start main

toys = scanner.find_toys(toy_names = ["SB-B11D", "SB-BD0A", "SB-E274"])

try:
    for toy in toys:  # fighting back against the bleak error exceptions
        with SpheroEduAPI(toy) as api:
            api.calibrate_compass()
            api.reset_aim()
except:
    print("Error!")
    sys.exit()

print(len(toys))

instructions = [multiprocessing.Queue() for i in range(len(toys))]

run_toy_threads(toys, instructions)

