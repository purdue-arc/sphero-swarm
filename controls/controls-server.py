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

lock = Lock()

def toy_manager(toy, id):
    global instructions

    with SpheroEduAPI(toy) as api:
        while True:
            if (len(instructions[id]) != 0):
                try:
                    lock.acquire()
                    instruction = instructions[id].pop(0)
                    if (instruction.type == 0):
                        # insert command to reset yaw
                        print("reset yaw")
                    elif (instruction.type == 1):
                        # insert command to reset locator
                        print("reset locator")
                    elif (instruction.type == 2):
                        api.set_main_led(instruction.color)
                        api.set_back_led(instruction.color)
                        api.set_front_led(instruction.color)
                    elif (instruction.type == 3):
                        api.roll(instruction.heading, instruction.speed, instruction.duration)
                finally:
                    lock.release()
                # end try
            # end if
        # end while
    # end with
# end toy_manager

def controls():
    global instructions

    s = socket.socket()
    port = 1234

    s.bind(('localhost', port))

    s.listen(5)

    c, address = s.accept()

    while (True):
        instruction = pickle.loads(c.recv(1024))
        print(instruction.type)
        if (instruction.type == 3):
            print(instruction.heading)
            print(instruction.speed)
            print(instruction.duration)

        try:
            lock.acquire()
            instructions[instruction.spheroID].append(instruction)
        finally:
            lock.release()
        # end try
    # end while
# end controls()

def run_toy_threads(toys):
    id = 0
    threads = []

    for toy in toys:
        thread = threading.Thread(target=toy_manager, args=[toy, id])
        threads.append(thread)
        thread.start()
        id += 1

    for thread in threads:
        thread.join()

    print("Ending function...")

controls()

"""
toys = scanner.find_toys()

global instructions

try:
    for toy in toys:  # fighting back against the bleak error exceptions
        with SpheroEduAPI(toy) as api:
            api.calibrate_compass()
            api.reset_aim()
except:
    print("Error!")
    sys.exit()

"""



