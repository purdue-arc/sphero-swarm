MARGIN = 1
DIRECTIONS = 8

N_SPHEROS = 3

GRID_WIDTH = 15
GRID_HEIGHT = 15
SIM_DIST = 50
FRAMES = 60

SPHERO_SIM_RADIUS = 15

SIM_WIDTH = GRID_WIDTH * SIM_DIST
SIM_HEIGHT = GRID_HEIGHT * SIM_DIST

EPSILON = 5

BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)

COLORS = [BLUE, RED, GREEN, YELLOW, PURPLE, ORANGE]

position_change = {
    0: (0, 0),
    1: (0, 1),
    2: (1, 1),
    3: (1, 0),
    4: (1, -1),
    5: (0, -1),
    6: (-1, -1),
    7: (-1, 0),
    8: (-1, 1)
}