from spherov2.sphero_edu import SpheroEduAPI
from spherov2 import scanner
import time

print("Looking for address")
sb_address = scanner.find_toy(toy_name="SB-CEB2")
print("Address found, connecting...")

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
                    api.set_speed(100)
                    heading = 0
                    while True:
                        api.set_heading(heading=heading)
                        heading += 10
                        time.sleep(0.001)
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