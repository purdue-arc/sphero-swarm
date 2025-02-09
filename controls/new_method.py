from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading

toys = scanner.find_toys(toy_names=["SB-B5A9", "SB-B11D"])

print(toys)

sb_list = []

def run_command(command, sb):
    match command[0]:
        case 'C':
            choosenColor = Color(0, 0, 0)
            match command[1]:
                case 'R':
                    choosenColor = Color(255, 0, 0)
                case 'G':
                    choosenColor = Color(0, 255, 0)
                case 'B':
                    choosenColor = Color(0, 0, 255)
            sb.set_main_led(choosenColor)
        case 'M':
            sb.roll(sb.get_heading(), 100, float(command[1:]))
        case 'R':
            sb.spin(int(command[1:]), 2)

try:
    for toy in toys:
        sb_list.append(SpheroEduAPI(toy).__enter__())

    commands = ["CG", "M2", "CR", "R90", "M2"]

    threads = []
    for command in commands:
        for sb in sb_list:
            thread = threading.Thread(target=run_command, args=[command, sb], daemon = True)
            threads.append(thread)
            thread.start()
    for thread in threads:
        thread.join()

finally:
    for sb in sb_list:
        sb.__exit__(None, None, None)

'''
for sb in sb_list:
    choosenColor = Color(r = 255, g = 0, b = 0)
    sb.set_main_led(choosenColor)
    sb.set_front_led(choosenColor)
    sb.set_back_led(choosenColor)
    sb.roll(0, 255, 0.5)
    sb.__exit__(None, None, None)
'''
