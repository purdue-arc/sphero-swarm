from spherov2 import scanner # turning works on relative direction, need to update code to match
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import keyboard
import sys
import time

toy = scanner.find_toy(toy_name = "SB-CEB2")

print(toy)

buffer = 5

with SpheroEduAPI(toy) as api:
    try:
        api.reset_aim()
        magBase = 0
    except:
        print("error")
        sys.exit()

    print("Start")

    on = True
    direction = 0

    while (on):
        if (keyboard.is_pressed('w')):
            if (direction != 0):
                api.set_speed(0)
                api.set_heading(0)
                direction = 0

            api.set_speed(100)
        elif (keyboard.is_pressed('q')):
            if (direction != 300):
                api.set_speed(0)
                api.set_heading(300)
                direction = 300

            api.set_speed(100)
        elif (keyboard.is_pressed('e')):
            if (direction != 60):
                api.set_speed(0)
                api.set_heading(60)
                direction = 60

            api.set_speed(100)
        elif (keyboard.is_pressed('d')):
            if (direction != 120):
                api.set_speed(0)
                api.set_heading(120)
                direction = 120

            api.set_speed(100)
        elif (keyboard.is_pressed('s')):
            if (direction != 180):
                api.set_speed(0)
                api.set_heading(180)
                direction = 180

            api.set_speed(100)
        elif (keyboard.is_pressed('a')):
            if (direction != 240):
                api.set_speed(0)
                api.set_heading(240)
                direction = 240

            api.set_speed(100)
        elif (keyboard.is_pressed('p')):
            on = False
        else:


            api.set_speed(0)
