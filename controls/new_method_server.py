from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
from threading import Lock
import Instruction
import time
import pickle
import socket

def connect_ball(toy, sb_list):
    sb = 0
    try:
        print("Connection Sucess")
        sb = SpheroEduAPI(toy).__enter__()
        sb_list.append(sb)
    except Exception:
        print("Connection Failure")

def run_command(instruction, sb):
    global on
    match (instruction.type):
        case 0:
            sb.set_main_led(instruction.color)
        case 1:
            sb.roll(sb.get_heading(), instruction.speed, instruction.duration)
        case 2:
            sb.spin(instruction.degrees, instruction.duration)
        case 3:
            on = False

def control():
    global on
    lock = Lock()
    s = socket.socket()
    port = 1234
    s.bind(('localhost', port))
    s.listen(5)
    print("Waiting for connection")
    c, address = s.accept()
    while (on):
        instructionList = pickle.loads(c.recv(1024))
        try:
            lock.acquire()
            for instruction in instructionList:
                if (instruction.type == 3):
                    on = False
                    print("TERMINATION COMMAND RECIEVED")
                if (not (instruction.spheroID < len(command_arr))):
                    print("index out of bounds")
                else:
                    command_arr[instruction.spheroID].append(instruction)
                    print(instruction.type)
        finally:
            lock.release()

toys = scanner.find_toys(toy_names=["SB-1840", "SB-76B3", "SB-B5A9"])
print(toys)
sb_list = []

global command_arr
command_arr = []
for i in range(0, len(toys), 1):
    command_arr.append([])
global on
on = True

try:
    cmd_thread = threading.Thread(target=control, daemon=True)
    cmd_thread.start()
    threads = []

    # attempt to quickly connect via multi-threading
    for toy in toys:
        thread = threading.Thread(target=connect_ball, args=[toy, sb_list], daemon=True)
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

    while (on):
        threads = []
        for i in range(0, len(command_arr), 1):
            if (len(command_arr[i]) != 0):
                thread = threading.Thread(target=run_command, args=[command_arr[i].pop(0), sb_list[i]], daemon = True)
                threads.append(thread)
                thread.start()
        for thread in threads:
            thread.join()

finally:
    on = False
    for sb in sb_list:
        sb.__exit__(None, None, None)
    cmd_thread.join()
