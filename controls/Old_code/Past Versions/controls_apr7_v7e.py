from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
import time

def toy_manager(toy, id):
    global commands
    with SpheroEduAPI(toy) as api:
        while True:
            print(id)
            global allReady
            global commands
            global newCommandDetector

            choosenColor = Color(r = 0, g = 0, b = 0)
            
            magBase = 0
            direction = 0
            numIterations = 0

            while True and commands[id] != []:
                print("{}: {}".format(id, commands[id][0]))
                if (commands[id][0] == "%"): # be very careful with this - needs to be the absolute last command!
                    return
                elif (commands[id][0] == "c"):
                    api.calibrate_compass() # not perfect - need feedback
                    magBase = api.get_compass_direction()
                    api.set_main_led(choosenColor)
                elif (commands[id][0] == "m"):
                    api.roll(magBase + direction, 255, 0.25)
                    time.sleep(0.5)
                elif (commands[id][0][0] == "R"):
                    print(commands[id][0][1:])
                    direction += int(commands[id][0][1:])
                    # probably need to graph sphero turning in order to get a good idea of what the rotate command should be
                elif (commands[id][0] == "Cred"):
                    choosenColor = Color(r = 255, g = 0, b = 0)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)
                elif (commands[id][0] == "Cgreen"):
                    choosenColor = Color(r = 0, g = 255, b = 0)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)
                elif (commands[id][0] == "Cblue"):
                    choosenColor = Color(r = 0, g = 0, b = 255)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)
                elif (commands[id][0] == "Cblack"):
                    choosenColor = Color(r = 0, g = 0, b = 0)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)
                elif (commands[id][0] == "Cwhite"):
                    choosenColor = Color(r = 255, g = 255, b = 255)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)
                elif (commands[id][0] == "null"):
                    pass
                else:
                    print(commands[id][0] + " in ball {} is an invalid command!".format(id))
                commands[id] = commands[id][1:]
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
    global newCommandDetector
    
    commands = []
    allReady = []

    command =  ["Cblue", "c", "m", "R90", "m", "%"]
    for toy in toys:
        commands.append(command) # matrix is needed for more complex commands
        allReady.append([0] * len(command))

def commandReading(toys):
    global commands
    global allReady
    global newCommandDetector

    fileNum = 0
    while True:
        fileName = "algorithm/Commands"+str(fileNum)+".txt" # Creating the file where current polymer commands will be stored
        try:
            file = open(fileName, "r")
            stringCommands = file.read()
            print(stringCommands)
            protoStringArr = stringCommands.split("\n") # each line is another sphero ball
            i = 0
            for commandString in protoStringArr:
                commands[i] = commandString.split(",") # each command is seperated by commas
                allReady[i] = [0] * len(commands[i])
                newCommandDetector[i].append(i)
                i += 1
            file.close()
            fileNum += 1
        except FileNotFoundError: # need to make a passing command system
            print("Looking for: " + fileName)
        time.sleep(1)

def run_toy_threads(toys):
    id = 0
    threads = []

    global commands
    global allReady
    global newCommandDetector # works on length to tell if new commands exist
    commands = []
    allReady = []
    newCommandDetector = []

    for toy in toys: # creating the array system used to allow for coordination
        commands.append([])
        allReady.append([])
        newCommandDetector.append([])

    thread = thread.Thread(target=commandReading, args = [toys])
    threads.append(thread)
    thread.start()

    for toy in toys:
        thread = threading.Thread(target=toy_manager, args=[toy, id])
        threads.append(thread)
        thread.start()
        id += 1
    
    for thread in threads:
        thread.join()
        
    print("Ending function...")

toys = scanner.find_toys() # can't use normal find toy in conjunction "SB-76B3", "SB-1840", "SB-B11D"
# seems to raise bleak exception errors if it is done that way 

print(toys)
run_toy_threads(toys)
