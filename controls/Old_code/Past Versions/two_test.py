from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.commands.drive import DriveFlags
import time

# toy_names = ["SB-1840", "SB-CEB2"]  # Replace with your actual Sphero names
# toys = [scanner.find_toy(name) for name in toy_names]
toys = scanner.find_toys(toy_names = ["SB-1840", "SB-CEB2"])

# Create API instances for both Spheros
spheros = [SpheroEduAPI(toy).__enter__() for toy in toys]
speed = 100
target = -25
tolerance = 0.5
prev_abs_distances = [0, 0]

try:
    for i in range(0, 1, 1):
        cur_distances = [0, 0]
        while any(d > target + tolerance or d < target - tolerance for d in cur_distances):
            for idx, sb in enumerate(spheros):
                direction_flag = DriveFlags.FORWARD
                direction = 1
                if cur_distances[idx] > target:
                    direction_flag = DriveFlags.BACKWARD
                    direction = -1
                
                sb._SpheroEduAPI__toy.drive_with_heading(speed, sb.get_heading(), direction_flag)

                updated_dist = sb.get_distance()
                print("Sphero {}: {}, {}".format(idx+1, updated_dist, prev_abs_distances[idx]))
                cur_distances[idx] += direction * (updated_dist - prev_abs_distances[idx])
                prev_abs_distances[idx] = updated_dist
                
                print("Sphero {} current distance: {}".format(idx+1, cur_distances[idx]))
            
            time.sleep(1 / 100)
        
        # Stop both Spheros
        for sb in spheros:
            sb.stop_roll()
        
        print("Attempt {}: Sphero 1: {}, Sphero 2: {}".format(i, cur_distances[0], cur_distances[1]))
        time.sleep(5)
        
        # Reset the system for both Spheros
        for idx, sb in enumerate(spheros):
            updated_dist = sb.get_distance()
            prev_abs_distances[idx] = updated_dist

finally:
    print("Final distances - Sphero 1: {}, Sphero 2: {}".format(cur_distances[0], cur_distances[1]))
    for sb in spheros:
        sb.__exit__(None, None, None)