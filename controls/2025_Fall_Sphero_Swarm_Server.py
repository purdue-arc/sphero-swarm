# PLEASE READ:
#   - Have Bluetooth on this device prior to running code, to avoid getting a WIN error if you are on Windows OS
#   - IN PROGRESS!!!

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
from Instruction import Instruction
import time

def generate_dict_map():
    try:
        ret_dict = dict([])
        with open("name_to_location_dict.csv", "r") as file:
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

# NEEDS METHOD TO SORT INTO CORRECT ORDERING PAIRS

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
    raise RuntimeError("Not all balls actually connected")

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
            print("Error occuring with: {}, reattempting".format(toy_address))
            attempts += 1
            continue

def connect_multi_ball(toy_addresses, ret_list, locations, max_attempts):
    # hopefully fast enough that control c'ing in this time should not be humanly reactable
    print("Connecting to Spheros...")
    # active thread tracker
    threads = []    

    # connecting to sb section
    for index in range(0, len(toy_addresses), 1):
        thread = threading.Thread(target=connect_ball, args=[toy_addresses[index], ret_list, locations[index], max_attempts])
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
    # brainstorming: the idea is wait for a set amount time, and then 
    # we check if they're all done - not futures, if still futures -  wait??? 

def run_command(sb, command):
    pass

# terminate ball to free it for future use
def terminate_ball(sb):
    sb.__exit__(None, None, None)

# terminate balls to allow it to be connected to in the future
# possibly unsafe - testing needed
def terminate_mutli_ball(sb_list):
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
    # note: still need to test that ordering isn't broken via sb address finding
    ball_names = ["SB-CEB2", "SB-B11D", "SB-76B3", "SB-1840", "SB-B5A9", "SB-BD0A", "SB-E274"]
    
    name_to_location_dict = generate_dict_map()
    locations = []
    for ball_name in ball_names:
        locations.append(name_to_location_dict[ball_name])

    # find the addresses to connect with
    toys_addresses = find_balls(ball_names, 5)

    # sb list and locations for coordinating it
    sb_list = [None] * len(name_to_location_dict)

    try: 
        connect_multi_ball(toys_addresses, sb_list, locations, 10)

    finally:
        # always attempt to disconnect after connecting to avoid manual resets
        terminate_mutli_ball(sb_list)

if __name__ == "__main__":
    main()
