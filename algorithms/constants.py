MARGIN = 0
DIRECTIONS = 8

ALL_DIRECTIONS = [1, 2, 3, 4, 5, 6, 7, 8]

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

N_SPHEROS = 2

# the number of nodes on the grid widthwise
GRID_WIDTH = 7

# the number of nodes on the grid heightwise
GRID_HEIGHT = 7

# the pixel distance between two nodes 
SIM_DIST = 50
FRAMES = 60

SPHERO_SIM_RADIUS = 15

SIM_WIDTH = (GRID_WIDTH-1) * SIM_DIST
SIM_HEIGHT = (GRID_HEIGHT-1) * SIM_DIST

EPSILON = 0.01

SPHERO_SPEED = 60
ROLL_DURATION = 0.8 # in seconds
TURN_DURATION = 0.5 # in seconds

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

SPHERO_TAGS = ['SB-B5A9', 'SB-BD0A']
INITIAL_POSITIONS = [(0,0), (2,0)]

