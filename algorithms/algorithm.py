import random
from constants import MARGIN
from bonded_groups import BondNetwork
from sphero import Sphero

class Algorithm:
    position_change = {
        1: (0, 1),
        2: (1, 1),
        3: (1, 0),
        4: (1, -1),
        5: (0, -1),
        6: (-1, -1),
        7: (-1, 0),
        8: (-1, 1)
    }

    def __init__(self, width, height, initial_positions):
        self.width = width
        self.height = height
        self.nodes = [ [0] * width] * height
        self.spheros = []
        id = 0
        for x, y in initial_positions:
            self.spheros.append(Sphero(id=id, x=x, y=y, direction=0))
            self.nodes[x][y] = id
            id += 1
        self.bond_network = BondNetwork(n=len(self.spheros))

    def find_sphero(self, id): # -> Sphero
        return self.spheros[id]

    def compute_target_position(self, sphero, direction): # -> (int, int)
        return (sphero.x + self.position_change[direction][0], sphero.y + self.position_change[direction][1])
    
    def is_valid_move(self, direction, sphero, id): # -> bool
        target_x, target_y = self.compute_target_position(direction=direction, sphero=sphero)
        if target_x < MARGIN or target_x >= self.width - MARGIN:
            return False
        if target_y < MARGIN or target_y >= self.height - MARGIN:
            return False
        return (not self.nodes[target_x][target_y] or
                self.bond_network.is_bonded(id1=id, id2=self.nodes[target_x][target_y]))

    def find_valid_move(self, sphero, possible_directions): # -> (int, array[int])
        direction = random.choice(possible_directions)
        while not self.is_valid_move(direction=direction, sphero=sphero) and possible_directions:
            possible_directions.remove(direction)
            direction = random.choice(possible_directions)
        return (direction, possible_directions) if possible_directions else (0, [])
    
    def find_bonded_group_move(self): # -> (int, array[int])
        possible_directions = [1, 2, 3, 4, 5, 6, 7, 8]
        bonded_group = self.bond_network.groups
        direction = None
        for id in bonded_group:
            sphero = self.find_sphero(id)
            direction, possible_directions = self.find_valid_move(sphero=sphero,
                                                                  possible_directions=possible_directions)
        return direction, possible_directions
    
    def update_nodes(self, sphero, direction):
        self.nodes[sphero.x][sphero.y] = 0
        target_x, target_y = self.compute_target_position(sphero=sphero, direction=direction)
        self.nodes[target_x][target_y] = sphero.id
    
    def update_bonded_group_move(self, bonded_group):
        direction, possible_directions = self.find_bonded_group_move(bonded_group=bonded_group)
        for id in bonded_group:
            sphero = self.find_sphero(id)
            sphero.update_direction(direction=direction)
            self.update_nodes(sphero=sphero, direction=direction)
    
    def update_grid_move(self):
        for bonded_group in self.bonded_groups:
            self.update_bonded_group_move(bonded_group=bonded_group)
