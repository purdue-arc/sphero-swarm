from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
import time

def control_toy(toy, id, commands): # need to make a new system sooner or later - just working on bare threads right now
    with SpheroEduAPI(toy) as api:
        choosenColor = Color(r = 255, g = 0, b = 0)
        api.set_front_led(choosenColor)
        api.set_back_led(choosenColor)
        # still needs more work (untested, also probably doesn't work on matrix specific to the BOLT)
        numIterations = 0
        while True or commands == []:    
            print("{}: {}".format(id, commands[0]))
            if (commands[0] == "%"):
                allReady[id] = 1
                break
            elif (commands[0] == "c"):
                api.calibrate_compass()
                api.set_compass_direction(0)
                pass
            elif (commands[0] == "m"):
                api.roll(0, 255, 0.5)
                time.sleep(0.5)
            elif (commands[0] == "r"):
                api.spin(90, 1) 
            # probably need to graph sphero turning in order to get a good idea of what the rotate command should be
            else:
                print(commands[0] + " in ball {} is an invalid command!".format(id))
            commands = commands[1:]
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
            
def run_toy_threads(toys):
    threads = []
    commands = []
    global allReady
    allReady = []
    command = "cmmsr%"
    for toy in toys:
        commands.append(command) # matrix is needed for more complex commands
        allReady.append([0] * len(command))
    id = 0
    for toy in toys:
        thread = threading.Thread(target=control_toy, args=[toy, id, commands[id]])
        threads.append(thread)
        thread.start()
        id += 1
    # while True: need to recieve commands in constantly updating format
    for thread in threads:
        thread.join()
    print("Ending function...")

# Find toys
toys = scanner.find_toys(toy_names = ["SB-76B3", "SB-B11D"])

print(toys)

run_toy_threads(toys)
