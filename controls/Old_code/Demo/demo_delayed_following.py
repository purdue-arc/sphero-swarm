import pickle
import socket
from Instruction import Instruction
from spherov2.types import Color
import time
import keyboard
from controls.Old_code.dictionary_creator import create_dict

def run():
    # first -> last to run
    toy_names = ["SB-1840", "SB-CEB2"]
    id_dict = create_dict()

    s = socket.socket()
    port = 1234
    s.connect(('localhost', port))

    instructions_list = []
    while True:
        last = len(instructions_list)
        if (keyboard.is_pressed("r")):
            instructions_list.append([0, 255, 0, 0])
        elif (keyboard.is_pressed("g")):
            instructions_list.append([0, 0, 255, 0])
        elif (keyboard.is_pressed("b")):
            instructions_list.append([0, 0, 0, 255])
        elif (keyboard.is_pressed("c")):
            instructions_list.append([0, 0, 0, 0])
        elif (keyboard.is_pressed("w")):
            instructions_list.append([1, 100, 0.1])
        elif (keyboard.is_pressed("s")):
            instructions_list.append([1, -100, 0.1])
        elif (keyboard.is_pressed("d")):
            instructions_list.append([2, -5, 0.1])
        elif (keyboard.is_pressed("a")):
            instructions_list.append([2, 5, 0.1])
        elif (keyboard.is_pressed(" ")):
            instructions_list.append([3])
            break
        print(instructions_list)
        buffered_instructions = []
        done = True
        if (last != len(instructions_list)):
            for spheroNum in range(0, len(toy_names), 1):
                index_of_command = len(instructions_list) - spheroNum - 1 
                if (index_of_command >= 0):
                    relevant_instruction = instructions_list[index_of_command]
                    spheroID = id_dict[toy_names[spheroNum]]
                    instruction_type = relevant_instruction[0]
                    instruction = None
                    match instruction_type:
                        case 0:
                            red = relevant_instruction[1]
                            green = relevant_instruction[2]
                            blue = relevant_instruction[3]
                            color = Color(red, green, blue)
                            instruction = Instruction(spheroID, instruction_type, color)
                        case 1:
                            speed = relevant_instruction[1]
                            duration = relevant_instruction[2]
                            instruction = Instruction(spheroID, instruction_type, speed, duration)
                        case 2:
                            degrees = relevant_instruction[1]
                            duration = relevant_instruction[2]
                            instruction = Instruction(spheroID, instruction_type, degrees, duration)
                        case 3:
                            instruction = Instruction(spheroID, instruction_type)
                        case _:
                            continue
                    buffered_instructions.append(instruction)
                    done = False
            if (not done):
                print("Continuing")
                s.send(pickle.dumps(buffered_instructions))
                buffer = s.recv(1024).decode()
            time.sleep(0.1)
    try:
        while (True):
            time.sleep(100000000)
    finally:
        s.close()

if __name__ == "__main__":
    run()
