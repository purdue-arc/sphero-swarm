from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

toys = scanner.find_toys(toy_names=["SB-B5A9", "SB-B11D"])

print(toys)

sb_list = []

for toy in toys:
    sb_list.append(SpheroEduAPI(toy).__enter__())

for sb in sb_list:
    choosenColor = Color(r = 255, g = 0, b = 0)
    sb.set_main_led(choosenColor)
    sb.set_front_led(choosenColor)
    sb.set_back_led(choosenColor)
    sb.roll(0, 255, 0.5)
    sb.__exit__(None, None, None)
