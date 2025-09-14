from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
import keyboard
import time

# current color
global CUR_COLOR
CUR_COLOR = (0, 0, 255)

# connect a ball and then return the object created
def connect_ball(toy_name, ret_list, location):
    sb = SpheroEduAPI(toy_name).__enter__()
    ret_list[location] = sb

def exec_command(sb, cur_instruction, prev_instruction):
    print(cur_instruction)
    if (cur_instruction == 1):
        sb.set_heading(0)
        sb.set_speed(100)
    elif (cur_instruction == 2):
        sb.set_heading(270)
        sb.set_speed(100)
    elif (cur_instruction == 3):
        sb.set_heading(180)
        sb.set_speed(100)
    elif (cur_instruction == 4):
        sb.set_heading(90)
        sb.set_speed(100)
    elif (cur_instruction == 5):
        global CUR_COLOR
        if (cur_instruction != prev_instruction):
            CUR_COLOR = (CUR_COLOR[-1], CUR_COLOR[0], CUR_COLOR[1])
            sb.set_main_led(Color(r = CUR_COLOR[0], g = CUR_COLOR[1], b = CUR_COLOR[2]))
    else:
        sb.set_speed(0)

# terminate ball to free it for future use
def terminate_ball(sb):
    sb.__exit__(None, None, None)

# find the toys and print what is found
toys = scanner.find_toys(toy_names = ["SB-76B3", "SB-E274", "SB-1840"])
print(len(toys))

# sb list and locations for coordinating it
sb_list = [0] * len(toys)
location = 0

# active thread tracker
threads = []

try: 
    # connecting to sb section
    for toy in toys:
        thread = threading.Thread(target=connect_ball, args=[toy, sb_list, location])
        threads.append(thread)
        thread.start()
        location += 1
    # reconnect the system now
    for thread in threads:
        thread.join()

    # instructions for running the code, synced
    threads = []    
    prev_instruction = 0
    instruction = 0
    while True:
        if (keyboard.is_pressed("w")):
            instruction = 1
        elif (keyboard.is_pressed("a")):
            instruction = 2
        elif (keyboard.is_pressed("s")):
            instruction = 3
        elif (keyboard.is_pressed("d")):
            instruction = 4
        elif (keyboard.is_pressed("c")):
            instruction = 5
        else:
            instruction = 0        
        
        # connecting to sb section
        for sb in sb_list:
            thread = threading.Thread(target=exec_command, args=[sb, instruction, prev_instruction])
            threads.append(thread)
            thread.start()
            location += 1
        
        # reconnect the system now
        for thread in threads:
            thread.join()
            
        time.sleep(0.1)
        prev_instruction = instruction

except:
    pass

finally:
    for sb in sb_list:
        terminate_ball(sb)
