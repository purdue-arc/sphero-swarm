from spherov2 import scanner # turning works on relative direction, need to update code to match
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
import time

class Molecule:
    def __init__(self, bolt, rgb):
        self.rgb = Color(r = rgb[0], g = rgb[1], b = rgb[2])
        self.bolt = bolt
        self.bolt.set_main_led(self.rgb)

    def update_color(self, red, green, blue):
        self.rgb = Color(r = int(red), g = int(green), b = int(blue))
        self.bolt.set_main_led(self.rgb)
        
    def roll(self, speed, var_time):
        self.bolt.roll(0, int(speed), float(var_time))

    def rotate(self, degrees):
        self.bolt.spin(int(degrees), int(degrees) / 40)
        self.bolt.reset_aim()

    def delay(self, var_time):
        time.sleep(float(var_time))

    def nodal_move(self, num_paths):
        direction = num_paths % 6

def toy_manager(toy, id):
    global latch
    global commands

    with SpheroEduAPI(toy) as api:
                
        molecule = Molecule(api, [0, 0, 0])

        while (latch[id] < len(commands[id])):
            
            current_command = commands[id][latch[id]]
            starting_letter = current_command[0]
            rest_of_command = current_command[1:].split(",")

            print("{}: {}".format(id, commands[id][latch[id]]))

            match starting_letter:
                case "M":
                    molecule.roll(*rest_of_command)
                case "R":
                    molecule.rotate(*rest_of_command)
                case "C":
                    molecule.update_color(*rest_of_command)
                case "D":
                    molecule.delay(*rest_of_command)
                case "N":
                    molecule.nodal_move(*rest_of_command)
                case _:
                    print(f"Doesn't match any preexisting commands: {current_command}")

            while True: # need to build in latch system
                exit_code = False
                
                for depths in latch:
                    if (latch[id] < depths):
                        exit_code = True
                        break
                    elif (latch[id] > depths):
                        break
                if (len(list(set(latch))) == 1): # if all values are the same within latch
                    exit_code = True

                if (exit_code):
                    break
                else:
                    time.sleep(0.01)
            latch[id] += 1

def run_toy_threads(toys):
    threads = []
    
    global commands
    global latch
    commands = []
    latch = [] 

    synced_movement = ["C0,255,0", "M100,0.4", "R90", "M100,0.3", "R-90", "D0.5", "M100,0.2"]

    for id in range(0, len(toys), 1):
        commands.append(synced_movement)
        latch.append(0)
        thread = threading.Thread(target=toy_manager, args=[toys[id], id], daemon=True)
        threads.append(thread)
        thread.start()
        
    for thread in threads:
        thread.join()
        
toys = scanner.find_toys(toy_names = ["SB-BD0A", "SB-E274"])

"""
try: 
    for toy in toys: # fighting back against the bleak error exceptions
        with SpheroEduAPI(toy) as api:
            # api.calibrate_compass()
            # api.reset_aim()
            pass
except:
    print("Error!")
    sys.exit()
"""

print(toys)

run_toy_threads(toys)
