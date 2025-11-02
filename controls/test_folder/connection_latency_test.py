'''
obj_list = range(0, 100, 1)
cur_pos = 0

num_sent_at_once = 7
terminate = False
while (not terminate):
    for i in range(0, num_sent_at_once, 1):
        if (i + cur_pos < len(obj_list)):
            print(obj_list[cur_pos + i], end=",")
        else:
            terminate = True
            break
    print("\n", end="")
    cur_pos += num_sent_at_once

print("All Done")
'''

# QUICK NOTE: EVEN THIS CURRENT PIPELINED SOLUTION IS BAD - AS THERE ARE certain slots that remain 
# "unused" - when one ball is taking a long time within its set. Maybe to make it even faster...
# make it push more into the moment it is done

from Fall_2025_Sphero_Swarm_Server import *
import time

ball_names = ["SB-E274", "SB-76B3", "SB-B11D", "SB-B5A9", "SB-BD0A"]
    
name_to_location_dict = generate_dict_map()
valid_sphero_ids = []
for ball_name in ball_names:
    valid_sphero_ids.append(name_to_location_dict[ball_name])
# sorted in ascending order
valid_sphero_ids.sort(key = lambda ball_id : ball_id)
print("ID's linked to initial ball names provided, sorted: {}".format(valid_sphero_ids))

# find the addresses to connect with
toys_addresses = find_balls(ball_names, 5)

# then sort the addresses to match csv ordering
address_sort(toys_addresses, name_to_location_dict)

# sb list has length of the number of valid ids
start_time = time.time()
sb_list = [None] * len(toys_addresses)

try: 
    # pipelined_connect_multi_ball(toys_addresses, sb_list, 3, 10)
    connect_multi_ball(toys_addresses, sb_list, 10)
finally:
    # always attempt to disconnect after connecting to avoid manual resets
    terminate_multi_ball(sb_list)

print("Time (s): {}".format(time.time() - start_time))

# hold on... is reconnecting faster???
start_time = time.time()
try: 
    # pipelined_connect_multi_ball(toys_addresses, sb_list, 3, 10)
    connect_multi_ball(toys_addresses, sb_list, 10)
finally:
    # always attempt to disconnect after connecting to avoid manual resets
    terminate_multi_ball(sb_list)
print("Time (s): {}".format(time.time() - start_time))

# not really