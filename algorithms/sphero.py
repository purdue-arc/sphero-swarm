import math

class Sphero:
    def __init__(self, id, x, y, previous_direction, direction, speed=1):
        self.id = id
        self.x = x
        self.y = y
        self.speed = speed
        self.previous_direction = previous_direction
        self.direction = direction

    def update_direction(self, direction):
        self.previous_direction = self.direction
        self.direction = direction

    def get_direction_change(self):
        return self.previous_direction - self.direction

    # checks whether spheros are one node apart

    def can_bond(self, adj_sphero):
        if (math.abs(self.x - adj_sphero.x) <= 1 and
            math.abs(self.y - adj_sphero.y) <= 1):
            return True
        return False


    def __str__(self):
        return f"{self.id}"
    
# TODO:
# remove update direction
# look at driver - look at differences at driver vs Sphero
# We want the driver code ot use the same functions
# so change the sphero class to use the similariaries of rthe driver 
# make it the same as driver 
# remove rotate
# we are using driver2
# remove velocity
# tdlr base off sphero.py off of driver2



# algorithms strucutre:
# - algorithms.py
#   - 2D grid (field) - Width x Height
#   - Each Cell has a value - 0 for no sphero, non zero for sphero ID 
# - simulation.py
#   - code to actually move it
# - sphero.py
#   - implement driver code changes, update or 8 directions
#   - parameters - [id, x, y, color] - no target_x/y
#   - 

# sphero.py is the class


# TODO LIST FOR Simulation -> 8 Directions

# Fill in Constants class
# Sphero class - update_direction
# Rewrite Driver code to call algoritms code
# Change simulation UI to have background as grid
# TODO: Documentation needed for using the driver 