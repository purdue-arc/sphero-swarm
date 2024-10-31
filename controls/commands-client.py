import pickle
import socket
from Instruction import Instruction

from spherov2 import scanner # turning works on relative direction, need to update code to match
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import multiprocessing
import threading
import time
import sys

s = socket.socket()
port = 12345

s.connect(('localhost', port))

while (True):
    nunIns = int(input("How many instructions would you like to send?"))
    instructions = []
    for i in range(nunIns):
        spheroID = int(input("What sphero would you like to send the instruction to? "))
        type = int(input("What type of instruction would you like to send? "))
        if (type == 0):
            instruction = Instruction(spheroID, type)
        elif (type == 1):
            instruction = Instruction(spheroID, type)
        elif (type == 2):
            red = int(input("R: "))
            green = int(input("G: "))
            blue = int(input("B: "))
            color = Color(red, green, blue)
            instruction = Instruction(spheroID, type, color)
        elif (type == 3):
            heading = int(input("Heading: "))
            speed = int(input("Speed: "))
            duration = int(input("Duration: "))
            instruction = Instruction(spheroID, type, heading, speed, duration)
        else:
            print("Enter a valid instruction type")
            continue

        instructions.append(instruction)
        # end if

    s.send(pickle.dumps(instructions))

# end while