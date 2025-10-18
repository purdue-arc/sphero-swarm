# B11D is broken

from Fall_2025_Sphero_Swarm_Server import *
from spherov2.types import Color

BLACK = Color(0, 0, 0)
GREY = Color(64, 64, 64)
WHITE = Color(255, 255, 255)
BLUE = Color(0, 0, 255)
ORANGE = Color(255, 128, 0)
GREEN = Color(0, 255, 0)
YELLOW = Color(255, 255, 0)
# darker orange
BROWN = Color(165, 42, 0)

# matrix must be 8 by 8 minimum
def draw_matrix(sb, matrix):
    for i in range(0, 8, 1):
        for j in range(0, 8, 1):
            sb.set_matrix_pixel(i, j, matrix[i][j])

MERCURY_MATRIX = [[BLACK] * 8,
                  [BLACK] * 8,
                  [BLACK, BLACK, BLACK, GREY, GREY, BLACK, BLACK, BLACK],
                  [BLACK, BLACK, GREY, GREY, GREY, GREY, BLACK, BLACK],
                  [BLACK, BLACK, GREY, GREY, GREY, GREY, BLACK, BLACK],
                  [BLACK, BLACK, BLACK, GREY, GREY, BLACK, BLACK, BLACK],
                  [BLACK] * 8,
                  [BLACK] * 8]

VENUS_MATRIX = [[BLACK] * 8, 
                [BLACK, BLACK, WHITE, BROWN, BROWN, BROWN, BLACK, BLACK],
                [BLACK, ORANGE, ORANGE, BROWN, BROWN, BROWN, BROWN, BLACK],
                [BLACK, ORANGE, ORANGE, BROWN, ORANGE, BROWN, BROWN, BLACK],
                [BLACK, WHITE, ORANGE, BROWN, BROWN, BROWN, BROWN, BLACK],
                [BLACK, ORANGE, ORANGE, BROWN, BROWN, ORANGE, BROWN, BLACK],
                [BLACK, BLACK, WHITE, ORANGE, BROWN, BROWN, BLACK, BLACK],
                [BLACK] * 8]

EARTH_MATRIX = [[BLACK] * 8, 
                [BLACK, BLACK, BLUE, BLUE, WHITE, WHITE, BLACK, BLACK],
                [BLACK, BLUE, GREEN, GREEN, GREEN, GREEN, GREEN, BLACK],
                [BLACK, BLUE, GREEN, BLUE, BLUE, GREEN, BLUE, BLACK],
                [BLACK, BLUE, GREEN, GREEN, GREEN, BLUE, BLUE, BLACK],
                [BLACK, BLUE, BLUE, BLUE, BLUE, GREEN, BLUE, BLACK],
                [BLACK, BLACK, WHITE, BLUE, BLUE, BLUE, BLACK, BLACK],
                [BLACK] * 8]

ball_names = ["SB-B11D", "SB-1840", "SB-B5A9", "SB-BD0A"]

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
sb_list = [None] * len(toys_addresses)

try: 
    connect_multi_ball(toys_addresses, sb_list, 10)

    # SB 0 is the sun
    # SB 1 is mercury
    # SB 2 is venus
    # SB 3 is earth
    # SB 4 is mars 

    sb_list[0].set_main_led(YELLOW)
    sb_list[0].set_front_led(YELLOW)
    sb_list[0].set_back_led(YELLOW)
    sb_list[0].set_left_led(YELLOW)
    sb_list[0].set_right_led(YELLOW)
    draw_matrix(sb_list[1], MERCURY_MATRIX)
    draw_matrix(sb_list[2], VENUS_MATRIX)
    draw_matrix(sb_list[3], EARTH_MATRIX)

    SPEEDS = [0, 50, 50, 50]
    headings = [0] * 4

    while True:
        try:
            for i in range(0, len(sb_list), 1):
                    sb_list[i].set_heading(heading=headings[i])
                    sb_list[i].set_speed(SPEEDS[i])
                    headings[i] += 10
            time.sleep(0.001)
        except KeyboardInterrupt:
            for sb in sb_list:
                sb.set_speed(0)

finally:
    terminate_multi_ball(sb_list)