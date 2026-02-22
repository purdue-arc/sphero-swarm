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
    
    def rotate_box(box, direction):
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
        self.valid_moves = ALL_DIRECTIONS.copy()

    def __str__(self) -> str:
        '''
        Returns a string representation of the BondedGroup with all attributes. Thanks Copilot
        '''
        sphero_ids = [sphero.id for sphero in self.spheros]
        return (f"BondedGroup(group_id={self.group_id}, size={self.size}, \n"
                f"center_id={self.center}, sphero_ids={sphero_ids}, \n"
                f"bounding_box(U,D,L,R)={self.box}), \n"
                f"valid_moves={self.valid_moves}")





