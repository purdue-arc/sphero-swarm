from .sphero import Sphero
from .constants import *
import math


class BondedGroup:
    def __init__(self, list_spheros: list[Sphero], id: int):
        self.group_id = id              # groups have unique ids starting at 1
        self.spheros = list_spheros     
        self.size = len(self.spheros)   
        self.box = [0,0,0,0]            # bounding box dimensions from center. order: U, D, L, R

        self.center = self.find_center() # ID of the center sphero (1, 2, 3, ...)
        
        self.valid_moves = ALL_DIRECTIONS.copy()       #  1-10

    def find_sphero(self, id):
        '''
        Returns the sphero object that mathches the inputted id
        '''
        for sphero in self.spheros:
            if sphero.id == id:
                return sphero
            
        print(f"Sphero {id} not in group {self.group_id}")
        return None

    def update_sphero_membership(self) -> None:
        '''
        gives all spheros this group's group_id, recalculates size, center, box dimensions
        '''
        for sphero in self.spheros:
            sphero.group_id = self.group_id
        
        # recalculate group 1 size
        self.size = len(self.spheros)

        # recalculate group 1 center
        self.update_center()
 
        # recalculate group 1 box FIXME we need to figure out box dimensions
        center_sphero = self.find_sphero(self.center)
        max_x = center_sphero.x
        max_y = center_sphero.y
        min_x = center_sphero.x
        min_y = center_sphero.y
        for sphero in self.spheros:
            max_x = max(max_x, sphero.x)
            max_y = max(max_y, sphero.y)
            min_x = min(min_x, sphero.x)
            min_y = min(min_y, sphero.y)
        self.box[0] = max_y - center_sphero.y # up  TODO we have to discuss which direction is up lol
        self.box[1] = max_x - center_sphero.x # right    
        self.box[2] = center_sphero.y - min_y # down
        self.box[3] = center_sphero.x - min_x # left

    def find_center(self) -> int:
        '''
        Returns the sphero_id of the sphero closest 
        to the average coordinate of all spheros in this group.
        '''

        # calculate average position in the group
        sum_x = 0
        sum_y = 0
        for sphero in self.spheros:
            sum_x += sphero.x
            sum_y += sphero.y

        average_position = (sum_x / self.size, sum_y / self.size)

        # find the sphero that is closest to this average point
        closest_sphero = self.spheros[0].id
        current_position = (self.spheros[0].x, self.spheros[0].y)

        closest_distance = math.dist(average_position, current_position)

        for sphero in self.spheros:
            current_position = (sphero.x, sphero.y)
            current_distance = math.dist(current_position, average_position) # current sphero dist to true center
            if current_distance < closest_distance:
                closest_sphero = sphero.id
                closest_distance = current_distance
        
        return closest_sphero
    
    def rotate_box(self, box, direction):
        '''
        Returns a box list rotated according to the inputted direction
        (9 = clockwise; 10 = counterclockwise)
        '''
        if direction == 9:
            return [box[3], box[0], box[1], box[2]]
        else:
            return [box[1], box[2], box[3], box[0]]
    
    def update_center(self) -> None:
        self.center = self.find_center()

    def reset_valid_moves(self) -> None:

        # Copy all valid moves
        self.valid_moves = ALL_DIRECTIONS.copy()

        # Remove rotations for single sphero groups
        if len(self.spheros) <= 1 and len(ALL_DIRECTIONS) > 8:
            self.valid_moves.remove(9)
            self.valid_moves.remove(10)

    def __str__(self) -> str:
        '''
        Returns a string representation of the BondedGroup with all attributes. Thanks Copilot
        '''
        sphero_ids = [sphero.id for sphero in self.spheros]
        return (f"\tBondedGroup(group_id={self.group_id}, size={self.size}, \n"
                f"\tcenter_id={self.center}, sphero_ids={sphero_ids}, \n"
                f"\tbounding_box(U,D,L,R)={self.box}), \n"
                f"\tvalid_moves={self.valid_moves}\n")





