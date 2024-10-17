from spherov2 import scanner # turning works on relative direction, need to update code to match
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import keyboard
import sys
import time

toy = scanner.find_toy()

print(toy)

with SpheroEduAPI(toy) as api:
    try:
        api.calibrate_compass()
        magBase = api.get_compass_direction()
    except:
        print("error")
        sys.exit()

    print("Start")

    while (True):
        if (keyboard.is_pressed('w')):
            # move forward

            api.set_heading(magBase)
            api.set_speed(200)
        elif (keyboard.is_pressed('s')):
            # move back

            api.set_heading(magBase + 180)
            api.set_speed(200)
        elif (keyboard.is_pressed('a')):
            # move left

            api.set_heading(magBase + 270)
            api.set_speed(200)
        elif (keyboard.is_pressed('d')):
            # move right

            api.set_heading(magBase + 90)
            api.set_speed(200)
        else:
            # stop

            api.set_speed(0)
