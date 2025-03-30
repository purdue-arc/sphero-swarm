import pickle
import socket
from Instruction import Instruction
from spherov2.types import Color
import time

def run():
    s = socket.socket()
    port = 1234

    s.connect(('localhost', port))

    instruction_read = [
        [[4], [4], [4], [4], [3]],
        [[0, 255, 0, 0], [1, 125, 1], [2, 90, 1], [1, 125, 1], [1, 125, 1], [3]],
        [[0, 255, 0, 0], [1, 125, 1], [2, 90, 1], [1, 125, 1], [1, 125, 1], [3]],
        [[4], [4], [4], [4], [3]],
        [[4], [4], [4], [4], [3]],
        [[0, 255, 0, 0], [1, 125, 1], [2, 90, 1], [1, 125, 1], [1, 125, 1], [3]]
    ]

    for instruction_num in range(0, len(instruction_read[0]), 1):
        instructions_list = []
        for spheroID in range(0, len(instruction_read), 1):
            current_instruction = instruction_read[spheroID][instruction_num]
            instruction_type = current_instruction[0]
            instruction = None
            match instruction_type:
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
                    continue
            instructions_list.append(instruction)
        s.send(pickle.dumps(instructions_list))
        buffer = s.recv(1024).decode()
        print("Sucess")
    try:
        while (True):
            time.sleep(100000000)
    finally:
        s.close()

if __name__ == "__main__":
    run()