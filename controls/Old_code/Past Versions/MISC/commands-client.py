import pickle
import socket
from Instruction import Instruction

from spherov2.types import Color

s = socket.socket()
port = 1234

s.connect(('localhost', port))

while (True):
    nunIns = int(input("How many instructions would you like to send?"))
    instructions = []
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
        elif (type == 3 or type == 4):
            instruction = Instruction(spheroID, type)
        else:
            print("Enter a valid instruction type")
            continue

        instructions.append(instruction)
        # end if

    s.send(pickle.dumps(instructions))

    buffer = s.recv(1024).decode()
    print("Instructions Finished")

# end while
