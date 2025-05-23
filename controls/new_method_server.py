from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.commands.drive import DriveFlags
from spherov2.types import Color
import threading
from threading import Lock
from threading import Barrier
import Instruction
import time
import pickle
import socket

TIME = 0.5

def connect_ball(toy, sb_list):
    sb = 0
    try:
        print("Connection Success")
        sb = SpheroEduAPI(toy).__enter__()
        sb_list.append(sb)
        print(sb)
    except Exception:
        print("Connection Failure")

def terminate_ball(sb):
    sb.__exit__(None, None, None)

def run_command(instruction, sb):
    global on
    print("{}: {}".format(sb._SpheroEduAPI__toy, instruction.type))
    match (instruction.type):
        case 0:
            sb.set_main_led(instruction.color)
        case 1:
            if (instruction.speed < 0):
                sb._SpheroEduAPI__toy.drive_with_heading(abs(instruction.speed), sb.get_heading(), DriveFlags.BACKWARD)
                time.sleep(instruction.duration)
                sb.stop_roll()
            else:
                sb.roll(sb.get_heading(), instruction.speed, instruction.duration)
        case 2:
            sb.spin(instruction.degrees, instruction.duration)
        case 3:
            on = False

    barrier.wait()



def control():
    global on
    lock = Lock()
    s = socket.socket()
    port = 1235
    s.bind(('localhost', port))
    s.listen(5)
    print("Waiting for connection")
    c, address = s.accept()
    while (on):
        try:
            instructionList = pickle.loads(c.recv(1024))
        except EOFError:
            print("EOFError")
            s.close()
            on = False
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

            barrier.wait()
            c.send("Done".encode())
        finally:
            lock.release()

toy_names = ["SB-B5A9", "SB-B11D", "SB-BD0A"]
#toy_names = ["SB-B5A9"]
toys = []
attempts = 0
while (len(toys) != len(toy_names) and attempts < 5):
    toys = scanner.find_toys(toy_names=toy_names)
    attempts += 1
print(toys)
if (len(toys) != len(toy_names) and attempts >= 5):
    raise RuntimeError("Not all balls actually connected")
sb_list = []
barrier = Barrier(len(toys) + 1)

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

    # attempt to quickly connect via multi-threading, may need to sort things out to make sense
    for toy in toys:
        thread = threading.Thread(target=connect_ball, args=[toy, sb_list], daemon=True)
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    print(sb_list)
    if (len(sb_list) != len(toy_names)):
        raise RuntimeError("Error: Not Actually Connected")

    while (on):
        threads = []
        for i in range(0, len(command_arr), 1):
            if (len(command_arr[i]) != 0):
                thread = threading.Thread(target=run_command, args=[command_arr[i].pop(0), sb_list[i]], daemon = True)
                threads.append(thread)
                thread.start()
        for thread in threads:
            thread.join()
        time.sleep(TIME)

finally:
    on = False
    threads = []
    for sb in sb_list:
        thread = threading.Thread(target=terminate_ball, args=[sb], daemon=True)
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    cmd_thread.join()
