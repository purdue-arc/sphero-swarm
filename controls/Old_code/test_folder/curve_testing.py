# idea... while in 50 speed
# 10, 1 mS delay creates very tight circle
# 5, 0.5 mS delay creates wider circle
# 1, 0.1 mS delay creates very wide circle
# 
# just varying increments seemed to work fine also 

# the idea for circular rotation is that 
# speed is practically constant so long as the value is greater than 50
# the angle of change and the time for each angle change is all that matters
# as a result, one can tell how long it will take for the entire system to make 1 cycle
# this determines radius using constant speed assumption via 2pi * r = total_time * speed

# maybe also need to add in material coefficients

from spherov2.sphero_edu import SpheroEduAPI
from spherov2 import scanner
import time
import math

print("Looking for address")
sb_address = scanner.find_toy(toy_name="SB-B11D")
print("Address found, connecting...")

'''
with SpheroEduAPI(sb_address) as api:
    while True:
        user_input = ""
        try:
            user_input = input("make: ")
        except KeyboardInterrupt:
            print("Ending program...")
            break
        match user_input:
            case "help":
                print("Avaliable commands\ncircle\nfig8\nsemicirclewave\nkill")
            case "circle":
                try:
                    speed = int(input("Speed: "))
                    heading_increment = int(input("Heading inc: "))
                    timing_between_updates = float(input("Wait time (in mS): ")) / 1000
                    api.set_speed(50)
                    heading = 0
                    while True:
                        api.set_heading(heading=heading)
                        heading += heading_increment
                        time.sleep(timing_between_updates)
                except KeyboardInterrupt:
                    api.set_speed(0)
            case "fig8":
                try:
                    api.set_speed(100)
                    heading = 0
                    change_of_sine = 1
                    while True:
                        api.set_heading(heading=heading)
                        heading = heading + (10 * change_of_sine)
                        if (heading >= 180 or heading <= -180):
                            change_of_sine *= -1
                        time.sleep(0.001)
                except KeyboardInterrupt:
                    api.set_speed(0)
            case "semicirclewave":
                try:
                    api.set_speed(100)
                    heading = 0
                    change_of_sine = 1
                    while True:
                        api.set_heading(heading=heading)
                        heading = heading + (10 * change_of_sine)
                        if (heading >= 90 or heading <= -90):
                            change_of_sine *= -1
                        time.sleep(0.001)
                except KeyboardInterrupt:
                    api.set_speed(0)
            case "kill":
                print("Ending program...")
                break
            case _:
                print("not found... use help for more info")
'''

# realistically, the only way to control rotation radius uses a combination of both
# speed and heading increments... however, heading increments has a larger effect

# small circle method -> breaks for very large radius
with SpheroEduAPI(sb_address) as api:            
    while True:
        try:
            # radius and time for complete rotation
            time_for_rotation = float(input("Time to Complete Rotation (s): ")) 
            radius_of_circle = float(input("Radius (cm): "))
            scaling_factor = float(input("Scaling factor: ")) 
            
            speed = min(255, int(radius_of_circle * 2 * math.pi / time_for_rotation * scaling_factor))
            print(speed)
            heading_increment = 1
            timing_between_updates = time_for_rotation / 360

            # speed = int(input("Speed: "))
            # heading_increment = int(input("Heading inc: "))
            # timing_between_updates = float(input("Wait time (in mS): ")) / 1000
            
            api.set_speed(speed)
            heading = 0
            while True:
                api.set_heading(heading=heading)
                heading += heading_increment
                time.sleep(timing_between_updates)
        except KeyboardInterrupt:
            api.set_speed(0)
            if (input("Continue? ") == "N"):
                break