# PLEASE READ:
#   - Have Bluetooth on this device prior to running code, to avoid getting a WIN error if you are on Windows OS
#   - IN PROGRESS!!!

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.commands.drive import DriveFlags
import threading
from controls.Instruction import Instruction
import time
import os
from algorithms.constants import SPHERO_TAGS

# USE THE FOLLOWING COMMAND TO RUN THIS FILE FROM THE ROOT:
# python -m controls.2025_Fall_Sphero_Swarm_Server   

# these for interfile communication, pickle turns objects into byte streams
import pickle
import socket

def generate_dict_map():
    try:
        ret_dict = dict([])
        # open the CSV relative to this file's directory so module can be run from repo root
        csv_path = os.path.join(os.path.dirname(__file__), "name_to_location_dict.csv")
        with open(csv_path, "r") as file:
            # purposefully purge first line
            line = file.readline()
            while (True):
                line = file.readline()
                if (not line):
                    break
                cleaned_line = line.strip().split(", ")
                ret_dict.update({cleaned_line[0] : int(cleaned_line[1])})
        return ret_dict
    except:
        raise RuntimeError("Dictionary method failed! Exiting code.")

# find avaliable toys in an area, and then if not all balls connected
# after a set number of attempts, this raises an error
def find_balls(names, max_attempts):
    for attempts in range(0, max_attempts, 1):
        print("Attempts to find Spheros: " + str(attempts + 1))
        # find the toys and print what is found
        toys = scanner.find_toys(toy_names = names)
        print("Balls found: {}".format(toys))
        if (len(toys) == len(names)):
            print("Found all Sphero balls")
            return toys
        else:
            print("Failed to find all Sphero balls, retrying...")
    # ran out of attempts
    raise RuntimeError("Not all balls found")

# now to sort the addresses
def address_sort(addresses, map_to_location):
    # this will sort from lowest to highest location in the csv,
    # this converts address to string then maps it using dictionary
    addresses.sort(key = lambda address : map_to_location[address.__str__().split()[0]])
    print("Sorted Addresses: {}".format(addresses))

# connect a ball and then return the object created to the list
def connect_ball(toy_address, ret_list, location, max_attempts):
    attempts = 0
    while (attempts < max_attempts):
        try:
            sb = SpheroEduAPI(toy_address).__enter__()
            ret_list[location] = sb
            break
        except KeyboardInterrupt:
            print("Please do not terminate... issues will arise if terminated during connection")
            continue
        except:
            attempts += 1
            print("Trying to connect with: {}, attempt {}".format(toy_address, attempts))
            continue

# currently, only really manages 3 at a time??? so maybe break it up to avoid insanely long waits
# future ideas
def connect_multi_ball(toy_addresses, ret_list, max_attempts):
    # hopefully fast enough that control c'ing in this time should not be humanly reactable
    print("Connecting to Spheros...") 

    # active thread tracker
    threads = []    

    # connecting to sb section
    for index in range(0, len(toy_addresses), 1):
        thread = threading.Thread(target=connect_ball, args=[toy_addresses[index], ret_list, index, max_attempts])
        threads.append(thread)
        thread.start()
    
    while True:
        # resync the system now
        try:
            for thread in threads:
                thread.join(timeout=None)
            break
        except KeyboardInterrupt:
            print("Connection ongoning... please don't interupt.") 
            continue

    # verify function
    print("Balls Connected: {}".format(ret_list))
    # brainstorming: if we start getting future type errors, double check here?
    
# now to gather instructions from server
# the command_array_2d must be formated such that it sorted with sphero id's ascending
# same with the valid_sphero_ids
def command_gathering(valid_sphero_ids, command_array_2d):
    s = socket.socket()
    # arbitrary non-priv port
    port = 1235
    s.bind(('localhost', port))
    # enables the system to handle up to 5 connections before refusing more
    s.listen(5)
    print("Waiting for connection to client...")
    # conn is the object required for comm with the other files
    conn, address = s.accept()
    # given this is the first and only connection to be made for now, 
    # can immediately send relevant information
    conn.send(pickle.dumps(valid_sphero_ids))

    global KILL_FLAG
    while (KILL_FLAG == 0):
        try:
            appending_array = [None] * len(valid_sphero_ids)
            instruction_list = pickle.loads(conn.recv(1024)) 
            for instruction in instruction_list:
                try:
                    # immediately terminate program
                    if (instruction.type == -2):
                        KILL_FLAG = 1
                        break
                    index = valid_sphero_ids.index(instruction.spheroID)
                    appending_array[index] = instruction
                except ValueError:
                    print("Attempting to send command to not connnected ball...")
                    continue
            if (KILL_FLAG == 0):
                command_array_2d.append(appending_array)
                conn.send("Done".encode())
        except EOFError:
            print("EOFError..., other process terminated")
            s.close()
            # finish all other proceesses, but now append a kill set command
            kill_array = []
            for id in valid_sphero_ids:
                kill_array.append(Instruction(id,-1))
            command_array_2d.append(kill_array)
            # exit for loop - return to main
            break
            
# the individual method for running a command on a sphero ball
def run_command(sb, command):
    global KILL_FLAG
    if (command != None):
        match (command.type):
            case -2:
                # really shouldn't happen, but just in case
                KILL_FLAG = 1
            case -1:
                KILL_FLAG = 1
            case 0:
                sb.set_main_led(command.color)
            case 1:
                if (command.speed < 0):
                    sb._SpheroEduAPI__toy.drive_with_heading(abs(command.speed), sb.get_heading(), DriveFlags.BACKWARD)
                    time.sleep(command.duration)
                    sb.stop_roll()
                else:
                    sb.roll(sb.get_heading(), command.speed, command.duration)
            case 2:
                sb.spin(command.degrees, command.duration)
            case 3:
                time.sleep(command.duration)

# runs one cycle of commands
def run_multi_command(sb_list, commands):
    # holds what processes are running right now
    threads = []

    for i in range(0, len(sb_list), 1):
        thread = threading.Thread(target=run_command, args=[sb_list[i], commands[i]])
        threads.append(thread)
        thread.start()

    while True:
        # resync the system now
        try:
            for thread in threads:
                thread.join(timeout=None)
            break
        except KeyboardInterrupt:
            print("Running commands right now... please don't interupt.") 
            continue

# terminate ball to free it for future use
def terminate_ball(sb):
    if (sb != None):
        sb.__exit__(None, None, None)

# terminate balls to allow it to be connected to in the future
def terminate_multi_ball(sb_list):
    # should be fast enough to avoid anything silly
    print("DO NOT TERMINATE - ENDING PROCESSES RUNNING")
    # use multi-threading to speed up close out process
    threads = []
    for sb in sb_list:
        if (type(sb) == SpheroEduAPI):    
            thread = threading.Thread(target=terminate_ball, args=[sb])
            threads.append(thread)
            thread.start()

    while True:
        try:            
            # reconnect the system now, should be safe???
            for thread in threads:
                thread.join(timeout=None)
            break

        except KeyboardInterrupt:
            print("KeyboardInterrupt caught, please do not terminate prematurely")
            continue

def main():
    # set up the global kill flag which is used to tell the system to close out after this command
    global KILL_FLAG
    KILL_FLAG = 0

    #ball_names = ["SB-B11D", "SB-1840", "SB-B5A9", "SB-BD0A"]
    ball_names = SPHERO_TAGS
    
    name_to_location_dict = generate_dict_map()
    valid_sphero_ids = []
    for ball_name in ball_names:
        valid_sphero_ids.append(name_to_location_dict[ball_name])
    # sorted in ascending order
    valid_sphero_ids.sort(key = lambda ball_id : ball_id)
    print("ID's linked to initial ball names provided, sorted: {}".format(valid_sphero_ids))

    # find the addresses to connect with
    toys_addresses = find_balls(ball_names, 5)

    # then sort the addresses to match csv ordering
    address_sort(toys_addresses, name_to_location_dict)

    # sb list has length of the number of valid ids
    sb_list = [None] * len(toys_addresses)

    try: 
        connect_multi_ball(toys_addresses, sb_list, 10)

        commands_array = []
        # set up server at this point in thread...
        cmd_gather_thread = threading.Thread(target=command_gathering, args=[valid_sphero_ids, commands_array])
        cmd_gather_thread.start()

        num_commands_run = 1
        while (KILL_FLAG == 0):
            if (len(commands_array) != 0):
                # print(commands_array)
                # print()
                # print()
                # print()
                # print(len(commands_array))
                # print()
                # print()
                # print()
                # print("Running command {}".format(num_commands_run))
                run_multi_command(sb_list, commands_array.pop(0))
                num_commands_run = num_commands_run + 1
            else:
                time.sleep(0.1)

    finally:
        # raise kill flag in case anything is still going
        KILL_FLAG = 1
        # always attempt to disconnect after connecting to avoid manual resets
        terminate_multi_ball(sb_list)
        
if __name__ == "__main__":
    main()