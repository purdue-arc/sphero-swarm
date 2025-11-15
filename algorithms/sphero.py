from constants import *
from math import atan, cos, sin, sqrt
import random

class Sphero:
    def __init__(self, id, x, y,
                 target_x=None, target_y=None,
                 previous_direction=0, direction=0, speed=1, color=BLACK):
        self.id = id
        self.x = x
        self.y = y
        self.true_x = x
        self.true_y = y
        self.target_x = target_x if target_x is not None else x
        self.target_y = target_y if target_y is not None else y
        self.previous_direction = previous_direction
        self.direction = direction
        self.speed = speed
        self.color = color

    def compute_rotation_target(self, direction, center):
        if (self.id != center.id):
            x_rel = self.x - center.x
            y_rel = self.y - center.y
            angle = atan(y_rel / x_rel) + direction
            target_x = int(cos(angle) * sqrt((x_rel ** 2) + (y_rel ** 2))) + center.x
            target_y = int(sin(angle) * sqrt((x_rel ** 2) + (y_rel ** 2))) + center.y
            radius = sqrt(x_rel ** 2 + y_rel ** 2)
        else:
            target_x = center.x
            target_y = center.y
            radius = 0
            
        return (target_x, target_y, radius)    
    
    def compute_translation_target(self, direction, position_change):
        return (self.x + position_change[direction][0], self.y + position_change[direction][1], 0)
    
    def compute_target_position(self, direction, center=None): # -> (int, int)
        if direction % 1 == 0:
            return self.compute_translation_target(direction, position_change) 
        else:
            return self.compute_rotation_target(direction, center)

    def update_target(self):
        """
        Update our sphero's target position given our current direction

        Args:
            None
        
        Returns:
            None
        """

        self.target_x, self.target_y, self.radius = self.compute_target_position(direction=self.direction,center=self)     

    def update_direction(self, direction):
        """
        Update our sphero's direction and previous direction given a direction

        Args:
            direction: (int) value between 0 and DIRECTIONS

        Returns:
            None
        """

        self.previous_direction = self.direction
        self.direction = direction

    def update_movement(self, direction):
        """
        Update a spheros direction and target position given a direction

        Args:
            direction: (int) value between 0 and DIRECTIONS

        Returns:
            None
        """
        self.update_direction(direction=direction)
        self.update_target()

    def get_direction_change(self):
        """
        Get the difference between our previous and current direction

        Args:
            None

        Returns:
           (int): Difference between previous and current direction
        """
        return self.previous_direction - self.direction

    def get_position_change(self):
        """
        Get the change in position given our sphero's direction.

        Parameters:
            None

        Returns:
            (int, int): Our sphero's change in position from moving in the direction it's chosen.
        """

        return position_change[self.direction]

    def can_bond(self, adj_sphero):
        """
        Determines if our sphero and another sphero are close enough to bond

        Args:
            adj_sphero: (Sphero) another sphero

        Returns:
            (bool): Is our sphero and the adjacent sphero close enough to bond?
        """
        if (abs(self.x - adj_sphero.x) <= 1 and
            abs(self.y - adj_sphero.y) <= 1):
            return True
        return False

    def __str__(self):
        return f"pos: {self.x}, {self.y}, id: {self.id}, direction: {self.direction}, target pos: {self.target_x}, {self.target_y}"
    
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

class LinkedSphero:
    def __init__(self, sphero):
        self.sphero = sphero
        self.id = sphero.id
        self.x = sphero.x
        self.y = sphero.y
        self.color = sphero.color
    
    @property
    def target_x(self):
        return self.sphero.target_x

    @property
    def target_y(self):
        return self.sphero.target_y
    
    @property
    def speed(self):
        return self.sphero.speed
    
    @property
    def direction(self):
        return self.sphero.direction
    
    def __str__(self):
        return f"pos: {self.x}, {self.y}, id: {self.id}, direction: {self.direction}, target pos: {self.target_x}, {self.target_y}"
    