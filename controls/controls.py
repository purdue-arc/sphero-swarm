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
    """
    Continuously reads associated instructions array to check for new instructions. When found, execute the instruction.

    :param toy: sphero toy
    :param id: associated id
    :param instructions: associated instructions array
    """

    print("start", id)
    print(toy)

    on = True

    with SpheroEduAPI(toy) as api:
        while on:
            if (not instructions.empty()):
                #try:
                    #lock.acquire()
                    instruction = instructions.get()
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
                    elif (instruction.type == 3): # stop
                        on = False
                #finally:
                    #lock.release()
                # end try
            # end if
        # end while
    # end with
    print("end")
# end toy_manager


def run_toy_threads(toys, instructions):
    """
    create individual threads for each toy

    :param toys: array of toys
    :param instructions: global 2d instructions array
    """

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

# end run_toy_threads()

def controls(instructions):
    """
    receive instructions from terminal and add them to global 2d instructions array

    :param instructions: global 2d instructions array
    """

    # get instructions from terminal
    while (True):
        nunIns = int(input("How many instructions would you like to send?"))
        instructionList = []
        for i in range(nunIns):
            spheroID = int(input("What sphero would you like to send the instruction to? "))
            type = int(input("What type of instruction would you like to send? "))
            if (type == 0):
                red = int(input("R: "))
                green = int(input("G: "))
                blue = int(input("B: "))
                color = Color(red, green, blue)
                instruction = Instruction(spheroID, type, color)
            elif (type == 1):
                speed = int(input("Speed: "))
                duration = float(input("Duration: "))
                instruction = Instruction(spheroID, type, speed, duration)
            elif (type == 2):
                degrees = int(input("Degrees: "))
                duration = float(input("Duration: "))
                instruction = Instruction(spheroID, type, degrees, duration)
            elif (type == 3):
                instruction = Instruction(spheroID, type)
            else:
                print("Enter a valid instruction type")
                continue
                # end if

        # add given instructions to global 2d instructions array
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


# start main

# find toys
toys = scanner.find_toys(toy_names = ["SB-B11D", "SB-1840"])
"""
try:
    for toy in toys:  # fighting back against the bleak error exceptions
        with SpheroEduAPI(toy) as api:5
            # api.calibrate_compass()
            api.reset_aim()
except:
    print("Error!")
    sys.exit()
"""

print(len(toys))

# create 2d instructions array
instructions = [multiprocessing.Queue() for i in range(len(toys))]

# create threads for each toy
run_toy_threads(toys, instructions)

# get instructions from terminal
