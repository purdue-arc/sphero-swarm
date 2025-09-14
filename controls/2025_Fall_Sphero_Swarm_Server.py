# PLEASE READ:
#   - Have Bluetooth on this device prior to running code, to avoid getting a WIN error if you are on Windows OS
#   - IN PROGRESS!!!

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
import time

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
def connect_ball(toy_name, ret_list, location):
    sb = SpheroEduAPI(toy_name).__enter__()
    ret_list[location] = sb

def connect_multi_ball(toy_names, ret_list):
    pass

# terminate ball to free it for future use
def terminate_ball(sb):
    sb.__exit__(None, None, None)

# terminate balls to allow it to be connected to in the future
# note: current method is unsafe - because ctrl c repeatedly generates more threads,
# which can end in an error that tries to exit nothing, due to targeting the sb ball more than once
def terminate_mutli_ball(sb_list):
    while True:
        # brainstorming: outside of loop, but within try except, create threads, but don't start
        # contains while, then create threads in while loop, exceptions close threads, then reopen 
        # then on the next cycle, should be safer because speed of closing threads should be fast enough
        # to be unreactable 
        try:
            print("DO NOT TERMINATE - ENDING PROCESSES RUNNING")

            # use multi-threading to speed up close out process
            threads = []
            for sb in sb_list:
                if (type(sb) == SpheroEduAPI):    
                    thread = threading.Thread(target=terminate_ball, args=[sb])
                    threads.append(thread)
                    thread.start()
            
            # reconnect the system now
            for thread in threads:
                thread.join()
            break

        except KeyboardInterrupt:
            print("KeyboardInterrupt caught, please do not terminate prematurely")
            # include command to kill all threads???
            continue

def main():
    ball_names = ["SB-B5A9", "SB-B11D", "SB-E274"]
    toys = find_balls(ball_names, 5)

    # sb list and locations for coordinating it
    sb_list = [None] * len(toys)
    location = 0

    # active thread tracker
    threads = []

    # now into the mass of code
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

        print(sb_list)
        # brainstorming: the idea is wait for a set amount time, and then 
        # we check if they're all done - not futures, if still futures - then 

    finally:
        # always attempt to disconnect after connecting to avoid manual resets
        terminate_mutli_ball(sb_list)

if __name__ == "__main__":
    main()
