from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.commands.drive import DriveFlags
import time

toy_name = "SB-BD0A"
toy = scanner.find_toy(toy_name=toy_name)

sb = SpheroEduAPI(toy).__enter__()
speed = 100
target = -25
tolerance = 0.5 # any lower might cause issues, may require I controls
prev_abs_distance = 0

try:
    for i in range(0, 1, 1):
        cur_distance = 0
        while (cur_distance > target + tolerance or cur_distance < target - tolerance):
            direction_flag = DriveFlags.FORWARD
            direction = 1
            if (cur_distance > target):
                direction_flag = DriveFlags.BACKWARD
                direction = -1
            sb._SpheroEduAPI__toy.drive_with_heading(speed, sb.get_heading(), direction_flag)

            updated_dist = sb.get_distance()
            print("{}, {}".format(updated_dist, prev_abs_distance))
            cur_distance += direction * (updated_dist - prev_abs_distance)
            prev_abs_distance = updated_dist
            
            print(cur_distance)
            time.sleep(1 / 100)
        sb.stop_roll()
        print("Attempt {}: {}".format(i, cur_distance))
        time.sleep(5)
        # reset the system
        updated_dist = sb.get_distance()
        prev_abs_distance = updated_dist

finally:
    print(cur_distance)
    sb.__exit__(None, None, None)
