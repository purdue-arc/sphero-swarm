import pickle #pickel to send data between the client and server (obj to byte stream)
import socket
from Instruction import Instruction
from spherov2.types import Color
import time

s = socket.socket()
port = 1234

s.connect(('localhost', port)) #connecting to the server

instruction_read = [ #creates a nested list to be sent to the client over pickel 
                    #first element is of instruction type defined by the cases below, each inner list is an instuction
    [[0, 255, 0, 0], [1, 150, 0.5], [2, 60, 0.5], [1, 120, 0.5], [2, 60, 0.5], [3]],
    [[0, 255, 0, 0], [1, 100, 0.5], [2, 90, 0.5], [1, 25, 3], [1, 50, 1], [3]],
    [[0, 255, 0, 0], [1, 75, 1], [2, 125, 0.5], [1, 75, 2.5], [2, 100, 4], [3]],
    [[0, 255, 0, 0], [1, 200, 0.25], [2, 180, 0.5], [1, 255, 0.25], [1, 100, 0.25], [3]],
    [[0, 255, 0, 0], [1, 125, 0.5], [2, 270, 0.5], [1, 200, 0.5], [2, 100, 5], [3]]
]

for instruction_num in range(0, len(instruction_read[0]), 1): #iterate through instructions
    instructions_list = []
    for spheroID in range(0, len(instruction_read), 1): #iterate over sphero robots
        current_instruction = instruction_read[spheroID][instruction_num]
        instruction_type = current_instruction[0] #get the instruction type 
        instruction = Instruction 
        match instruction_type: #takes the instruction list and populates the insturction object
            case 0:
                red = current_instruction[1]
                green = current_instruction[2]
                blue = current_instruction[3]
                color = Color(red, green, blue)
                instruction = Instruction(spheroID, instruction_type, color)
            case 1:
                speed = current_instruction[1]
                duration = current_instruction[2]
                instruction = Instruction(spheroID, instruction_type, speed, duration)
            case 2:
                degrees = current_instruction[1]
                duration = current_instruction[2]
                instruction = Instruction(spheroID, instruction_type, degrees, duration)
            case 3:
                instruction = Instruction(spheroID, type)
            case _:
                print("Invalid formatting")
                continue
        instructions_list.append(instruction)
    s.send(pickle.dumps(instructions_list)) #use pickel to send the instruction list to the server
    time.sleep(0.5)
    print("Sucess")
s.close()
