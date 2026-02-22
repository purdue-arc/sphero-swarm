import random
from .constants import *
from .swarm import Swarm
from .sphero import Sphero
from .bonded_group import BondedGroup
from typing import cast
from math import hypot

class Algorithm:
    def __init__(self, grid_width, grid_height, spheros: list[Sphero]):
        
        self.grid_width = grid_width
        self.grid_height = grid_height

        # 2D arrays representing the nodes of our grid
        # grid[i][j] = 0 means no sphero is on the node
        # grid[i][j] != 0 means that the sphero with the id of value grid[i][j] is at that node
        self.current_grid = [ [0 for _ in range(grid_height)] for _ in range(grid_width)] 
        self.next_grid = [ [0 for _ in range(grid_height)] for _ in range(grid_width)] 

        self.n_spheros = len(spheros)

        # initialize bonded_groups
        self.bonded_groups = []
        id = 0
        for sphero in spheros:
            self.bonded_groups.append(BondedGroup([sphero], id))
            id += 1
            


    def __str__(self) -> str:
        return_str = 'Algorithm\n'
        for group in self.bonded_groups:
            return_str += '\t' + str(group) + '\n'
        return return_str


    def move_groups(self):
        '''
        for each group: 
            valid_move = self.find_group_move(group)
            if valid_move == -1 there are no valid moves, don't do anything
                we still have to update our stuff tho
            if valid_move == 1-8 
                update all necessary attributes for a translation
            if valid_move == 9 or 10 
                update all necessary attributes for a rotation
            
            Things that will be updated for each move:
            - next_grid for each sphero in each group
            - target position for each sphero in each group
            - direction & previous direction 

        at the end, call flip() to make current_grid = next_grid and to wipe next_grid
        '''
        for group in self.bonded_groups:
            valid_move = self.find_group_move(group)
            # TODO Alan


    def find_group_move(self, group: BondedGroup)-> int:
        '''
        TODO

        randomly select a translation or a rotation from group.valid_moves
        take out that option from the group.valid_moves
        check if it's valid 
            if it's translation, check by calling self.check_translation(move)
            else do some special stuff for checking rotation of the group TODO @John
        if it is valid, 
            reset valid_directions to be 1-10 again and 
            return the move direction
        if it isn't, 
            don't reset valid_directions
            keep trying to find a valid move
        if we run out of valid_directions to try
            reset 
            return -1
        '''
        #reset the group valid moves
        group.reset_valid_moves()

        while True:

            cur_direction = random.choice(group.valid_moves)
            group.valid_moves.remove(cur_direction)

            if cur_direction <= 8: # if it's a translation, check
                valid_move = True
                for sphero in group.spheros:
                    if not self.check_translation(sphero, cur_direction):
                        valid_move = False
                if valid_move:
                    return cur_direction

            else: # it's a rotation, check rotation validity
                assert False, 'rotation checking not implemented yet (delete this line when ur done)'
                # TODO implement check_rotation() @John
                valid_move = self.check_rotation(group, cur_direction)

    def check_translation(self, sphero: Sphero, move: int) -> bool:
        '''
        Only to be used for checking translations (moves 1-8)
        for each sphero in self.spheros, check if the move will:
            1. go out of bounds
            2. go where another sphero is in self.next_grid
        '''   
        # check for a translation
        if move in position_change.keys():
            dx, dy = position_change[move]

            in_bounds = (MARGIN <= sphero.x + dx < self.grid_width - MARGIN and 
                        MARGIN <= sphero.y + dy < self.grid_height - MARGIN)

            no_collisions = self.next_grid[sphero.x + dx][sphero.y + dy]
            return in_bounds and no_collisions
        # check for a rotation
        else:
            assert False, 'Do not use this function to check rotational moves!'
    
    def check_rotation(self, group: BondedGroup, move: int) -> bool:
        '''
        TODO @John, for a group, check if the rotation is valid. 
        '''
        assert move == 9 or move == 10, 'Do not use this function to check translational moves!'



   
    # def find_valid_move(self, sphero, possible_directions): # -> List[int]
    #     """
    #     Find a valid direction for a sphero given a list of possible directions

    #     Args:
    #         sphero: (Sphero) the passed in sphero
    #         possible_directions: (List[int]) a list of possible directions

    #     Returns:
    #         (List[int]): a list of all valid directions for the given sphero
    #     """
    #     for direction in possible_directions[:]:
    #         if not self.is_valid_move(direction=direction, sphero=sphero):
    #             possible_directions.remove(direction)
    #     return possible_directions if possible_directions else []
    

    # def find_bonded_group_move(self, bonded_group): # -> int
    #     """
    #     Find a valid direction for the bonded group

    #     Args:
    #         bonded_group: (List[int]) an array of sphero ids apart of the same bonded group

    #     Returns:
    #         (int): a valid direction for the bonded group
    #     """

    #     possible_directions = ALL_DIRECTIONS.copy()
    #     direction = None
    #     for id in bonded_group:
    #         sphero = self.find_sphero(id)
    #         possible_directions = self.find_valid_move(sphero=sphero,
    #                                                     possible_directions=possible_directions)
    #     direction = random.choice(possible_directions) if possible_directions else 0
    #     return direction
    
    # change to flip()
    def update_nodes(self, sphero):
        """
        Update the nodes array with the target position of the sphero

        Args:
            sphero: (Sphero) a passed in sphero
        
        Returns:
            None
        """
        
        self.nodes[sphero.x][sphero.y] = 0
        self.nodes[sphero.target_x][sphero.target_y] = sphero.id
    
    def update_bonded_group_move(self, bonded_group):
        """
        Update the direction of the bonded group and the grid

        Args:
            bonded_group: (List[int]) a list of sphero id's apart of the same bonding group

        Returns: 
            None
        """
        
        direction = self.find_bonded_group_move(bonded_group=bonded_group)
        for id in bonded_group:
            sphero = self.find_sphero(id)
            if sphero is not None:
                sphero.update_movement(direction=direction)
                self.update_nodes(sphero=sphero)
            else:
                # Should never happen
                raise NotImplementedError()
  
    def update_grid_move(self):
        """
        Update the movement for all bonded groups

        Args:
            None
        
        Returns:
            None
        """

        for bonded_group in self.swarm.bonded_groups:
            self.update_bonded_group_move(bonded_group=bonded_group)

    # change
    def update_sphero_bonds(self, sphero): 
        """
        Given a sphero, bond to all spheros that can bond to it

        Args:
            sphero: (Sphero) the passed in sphero

        Returns:
            None
        """

        # check all surrounding spheros
        for direction in range(1, DIRECTIONS + 1):
            adj_x, adj_y = sphero.compute_target_position(direction=direction)

            # if the surrounding position is in bounds
            if self.in_bounds(adj_x, adj_y):
                adj_id = self.nodes[adj_x][adj_y]
                if adj_id:
                    adj_sphero = self.find_sphero(id=adj_id)

                    # bond both spheros if they can bond
                    if sphero.can_bond(adj_sphero=adj_sphero):
                        new_group_index = self.swarm.combine(id1=sphero.id, id2=adj_id)

                        # determine new pivot sphero for resulting group
                        self.swarm.bonded_group_centers[new_group_index] = self.calculate_bonded_group_center(self.swarm.bonded_groups[new_group_index])
    
    def update_grid_bonds(self):
        """
        Update the bonds for all spheros

        Args:
            None

        Returns:
            None
        """

        for sphero in self.spheros:
            self.update_sphero_bonds(sphero=sphero)

# def generate_colors(self): # -> List[color]
    #     """
    #     Generate a list of colors, with length equal to the number of spheros

    #     Args:
    #         None

    #     Returns:
    #         List[colors]: a list of colors, with length equal to the number of spheros
    #     """

    #     colors = []
    #     for i in range(self.n_spheros):
    #         colors.append(COLORS[i % len(COLORS)])
    #     return colors

    # def random_initial_position(self): # -> (int, int)
    #     """
    #     Generate a random initial position on the grid that is both in bounds and
    #     doesn't collide with another sphero

    #     Args:
    #         None

    #     Returns:
    #         (int, int): a valid random initial position
    #     """

    #     x = random.randint(MARGIN, self.grid_width - MARGIN - 1)
    #     y = random.randint(MARGIN, self.grid_height - MARGIN - 1)
    #     while self.nodes[x][y]:
    #         x = random.randint(MARGIN, self.grid_width - MARGIN - 1)
    #         y = random.randint(MARGIN, self.grid_height - MARGIN - 1)

    #     # fill in board with temporary id
    #     self.nodes[x][y] = -1
    #     return x, y

    # def generate_random_grid(self): # -> List[int]
    #     """
    #     Generate a random set of initial positions for all spheros on the grid

    #     Args:
    #         None
        
    #     Returns:
    #         List[int]: a list of random intiial positions, with length equal to the number of spheros
    #     """

    #     positions = []
    #     for _ in range(self.n_spheros):
    #         x, y = self.random_initial_position()
    #         positions.append((x, y))
    #     return positions

    # def find_sphero(self, id): # -> Sphero
    #     """
    #     The sphero object that has the specified id

    #     Args:
    #         id: (int) the sphero's id
        
    #     Returns:
    #         (Sphero): the sphero object that has the specified id
    #     """
    #     if id:
    #         return self.spheros[id - 1]
    #     return None



    # def calculate_bonded_group_center(self, group):
    #     """
    #     Calculate the id of the sphero to be used as the pivot point for the bonded group

    #     Args:
    #         bonded group (swarm.bonded_groups[index])

    #     Returns:
    #         pivot sphero id (sphero.id)
    #     """

    #     total_x = 0
    #     total_y = 0
    #     n = 0

    #     for id in group:
    #         sphero = self.find_sphero(id)
    #         total_x += sphero.x
    #         total_y += sphero.y
    #         n += 1

    #     x_avg = total_x / n
    #     y_avg = total_y / n

    #     closest_sphero = 0
    #     closest_distance = -1

    #     for id in group:
    #         sphero = self.find_sphero(id)

    #         distance = hypot(x_avg - sphero.x, y_avg - sphero.y)

    #         if (closest_distance == -1) or (distance < closest_distance):
    #             closest_distance = distance
    #             closest_sphero = id
    

    #     return closest_sphero