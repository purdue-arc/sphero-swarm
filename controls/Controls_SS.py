from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
import time

def toy_manager(toy, id):
    global recieveNew
    global commands
    with SpheroEduAPI(toy) as api:
        while True:
            if recieveNew == True:
                recieveNew = False
                control_toy(api, id, commands[id])
            else:
                exit() # temp measure to prevent infinite loop

def control_toy(api, id, command):
    global allReady
    choosenColor = Color(r = 255, g = 0, b = 0)
    api.set_main_led(choosenColor)
    api.set_front_led(choosenColor)
    api.set_back_led(choosenColor)
    direction = 0
    # doesn't work on matrix, but does work on the positional lights
    numIterations = 0
    while True and command != []:
        print("{}: {}".format(id, command[0]))
        if (command[0] == "%"):
            allReady[id] = 1
            break
        elif (command[0] == "c"):
            api.calibrate_compass()
            api.set_main_led(choosenColor)
        elif (command[0] == "m"):
            api.roll(api.get_compass_direction() + direction, 255, 0.5)
            time.sleep(0.5)
        elif (command[0] == "r"):
            direction += 90
        # probably need to graph sphero turning in order to get a good idea of what the rotate command should be
        else:
            print(command[0] + " in ball {} is an invalid command!".format(id))
        command = command[1:]
        allReady[id][numIterations] = 1
        while True:
            ready = True
            for readiness in allReady:
                if (readiness[numIterations] == 0):
                    ready = False
                    break
            if (ready):
                break
        numIterations += 1
        time.sleep(1)

def commandInputs(toys): # needs to be able to consistently take in data
    global commands
    global allReady
    
    commands = []
    allReady = []

    command = "cmrm%"
    for toy in toys:
        commands.append(command) # matrix is needed for more complex commands
        allReady.append([0] * len(command))
            
def run_toy_threads(toys):
    id = 0
    threads = []
    
    global commands
    global allReady
    global recieveNew

    recieveNew = True

    commandInputs(toys)

    for toy in toys:
        thread = threading.Thread(target=toy_manager, args=[toy, id])
        threads.append(thread)
        thread.start()
        id += 1
    
    for thread in threads:
        thread.join()
    print("Ending function...")

# Find toys
toys = scanner.find_toys(toy_names = ["SB-76B3"]) # "SB-B11D"
print(toys)

try:
    run_toy_threads(toys)
except KeyboardInterrupt:
    print("Force terminating function.")