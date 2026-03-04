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
        api.reset_aim()
        magBase = 0
    except:
        print("error")
        sys.exit()

    print("Start")

    on = True
    for i in range(4):

        api.set_heading(magBase)
        api.set_speed(100)
        time.sleep(1)
        api.set_speed(0)
        time.sleep(0.5)
        magBase = magBase + 90
    
   