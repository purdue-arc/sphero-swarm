# the number of nodes on the grid widthwise
GRID_WIDTH = 9

# the number of nodes on the grid heightwise
GRID_HEIGHT = 9

SPHERO_TAGS = [
    'SB-45B0',
    'SB-0439',
    'SB-7672'
]
'''
    'SB-E274',
    'SB-1840'
]
'''

INITIAL_POSITIONS = [(0,0), (0,3), (3, 3)] # , (3,0), (3,3), (3, 6)] #, (8,0), (8,4), (8, 8)]#, (3, 4), (4, 4), (4, 1)]
# One "head" or "tail" per sphero; length must match N_SPHEROS
INITIAL_TRAITS = ["head", "tail", "tail"] # , "tail", "tail", "tail"] #, "tail", "head", "tail"]
MAX_MONOMERS = 3  # max spheros allowed per bonded group
# INITIAL_POSITIONS = [(0,0), (0,4), (4, 0), (4,4), (2,2)]#, (3, 1)]
#INITIAL_POSITIONS = [(0,0), (0,1), (0, 2), (0,3), (0,4), (0, 5)]

N_SPHEROS = len(INITIAL_POSITIONS)

ARC_ROTATION = False # Flag for using arced movements vs straight line movements in rotations.

MARGIN = 0
DIRECTIONS = 8

ALL_DIRECTIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]   # WITH rotation
# ALL_DIRECTIONS = [1, 2, 3, 4, 5, 6, 7, 8]        # NO rotation

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
# the pixel distance between two nodes 
SIM_DIST = 50
FRAMES = 60

SPHERO_SIM_RADIUS = 15

SIM_WIDTH = (GRID_WIDTH-1) * SIM_DIST
SIM_HEIGHT = (GRID_HEIGHT-1) * SIM_DIST

EPSILON = 0.01

SPEED_SCALAR = 2 # Set to 1 for original speed
SPHERO_SPEED = 60 * SPEED_SCALAR
SPHERO_DIAGONAL_SPEED = 76 * SPEED_SCALAR # 60 * sqrt(2), but adjusted for acceleration. Use 76 for SPEED 60. Thanks to jack for testing this
ROLL_DURATION = 0.8 # in seconds
TURN_DURATION = 0.5 # in seconds

SIM_SPEED = 1 # DO NOT SET THIS TOO HIGH!!!

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
