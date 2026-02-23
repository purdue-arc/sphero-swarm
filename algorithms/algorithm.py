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
        # put the spheros into the current_grid
        for sphero in spheros:
            self.current_grid[sphero.x][sphero.y] = sphero.id

        self.n_spheros = len(spheros)

        # initialize bonded_groups
        self.bonded_groups = []
        id = 1
        for sphero in spheros:
            self.bonded_groups.append(BondedGroup([sphero], id))
            id += 1

            


    def __str__(self) -> str:
        return_str = 'Algorithm\n'
        for group in self.bonded_groups:
            return_str += str(group) + '\n'
        return return_str


    def bond_all_groups(self) -> None:
        '''
        for each group
            for each sphero
                check in each sphero's valid directions

                if there is a neighboring sphero in one of the sphero's neighboring directions
                that doesn't belong to the same group, bond the two groups.
        '''
        for group in self.bonded_groups:
            if len(group.spheros) == 0:
                continue #empty group
            for sphero in group.spheros:
                for direction in sphero.bonding_directions:

                    dx, dy = direction # get the component directions

                    # is the neighbor coordinate we're about to look at in bounds?
                    in_bounds = (MARGIN <= sphero.x + dx < self.grid_width - MARGIN and 
                        MARGIN <= sphero.y + dy < self.grid_height - MARGIN)

                    if not in_bounds:
                        continue

                    neighbor_id = self.current_grid[sphero.x + dx][sphero.y + dy]
                    neighbor_sphero = self.find_sphero(neighbor_id)

                    if not neighbor_sphero:
                        continue
                    print('in bounds, neighbor_spheros exist')

                    # the neighboring sphero belongs to another group; we have to bond
                    if neighbor_sphero.group_id != sphero.group_id:
                        print(f'bond {sphero} with {neighbor_sphero}')
                        self.bond_two_groups(sphero.group_id, neighbor_sphero.group_id)
    
    def bond_two_groups(self, group_1_id, group_2_id) -> BondedGroup:
        '''
        gives all of group 2's spheros to group 1
        returns group 1
        '''
        print('bonding ', group_1_id, group_2_id)
        group_1 = self.find_group(group_1_id)
        group_2 = self.find_group(group_2_id)
        assert group_1 and group_2, 'should be valid group ids passed into bond_two_groups!!!'

        for sphero in group_2.spheros:

            # put in group 1
            group_1.spheros.append(sphero)

            # TODO update bonding rules if necessary

        # update spheros group_id in group 1
        group_1.update_sphero_membership()

        # reset everything in group 2 
        group_2.spheros = []
        group_2.size = 0
        group_2.box = [0,0,0,0]
        group_2.center = -1

        self.bonded_groups.remove(group_2)
    
    def find_sphero(self, id: int) -> Sphero:
        '''
        returns Sphero whose id matches in the passed in id
        else -1
        '''
        for group in self.bonded_groups:
            for sphero in group.spheros:
                if sphero.id == id:
                    return sphero
        return None
    
    def find_group(self, id: int) -> BondedGroup:
        '''
        returns BondedGroup whose group_id matches in the passed in id
        else -1
        '''
        for group in self.bonded_groups:
            if group.group_id == id:
                return group
        return None

    def move_all_groups(self):
        '''
        for each group: 
            valid_move = self.find_group_move(group)
            if valid_move == 0 there are no valid moves, don't do anything
                we still have to update our stuff tho
            if valid_move == 1-8 
                update all necessary attributes for a translation
            if valid_move == 9 or 10 
                update all necessary attributes for a rotation
            
            Things that will be updated for each move:
            - next_grid for each sphero in each group
            - target position for each sphero in each group
            - direction & previous direction 

        at the end, make current_grid = next_grid and to wipe next_grid
        '''
        # move each group
        for group in self.bonded_groups:

            if len(group.spheros) == 0:
                continue #empty group

            # find a valid move for the group
            valid_move = self.find_group_move(group) # will return a valid move for group, error checking done
            print(f"Group: {group.group_id}\tDirection: {valid_move}")

            if valid_move >= 0 and valid_move <= 8: # for staying still (0) / translation (1 to 8)

                # print("Translation")

                dx, dy = position_change[valid_move]

                for sphero in group.spheros:
                    # set the target
                    sphero.target_x = sphero.x + dx
                    sphero.target_y = sphero.y + dy

                    # fill in next_grid spots
                    self.next_grid[sphero.target_x][sphero.target_y] = sphero.id

                    # update prev direction, direction
                    sphero.update_direction(valid_move)

            else: # valid_move is 9 or 10, aka a rotation.
                '''
                check if the move is valid by "boxing out" the rotation area.
                    check if anything in the 'box' is an ID not belonging to the group
                    check if anything in the 'box' will go out of bounds of the grid    

                for each sphero
                    matrix transform to get new target position
                    fill in next_grid spots
                    update prev direction, direction.
                '''

                print("Rotation")

                # Calculate the area to block
                center_x = self.find_sphero(group.center).x
                center_y = self.find_sphero(group.center).y
                rotated_box = group.rotate_box(group.box, valid_move)

                # Block out box for collisions
                for x in range(center_x - rotated_box[3], center_x + rotated_box[1]):
                    for y in range(center_y - rotated_box[2], center_y + rotated_box[0]):
                        self.next_grid[x][y] = -1

                # Move the spheros
                for sphero in group.spheros:
                    
                    # Calculate target position
                    if valid_move == 9: # Clockwise
                        sphero.target_x = (sphero.y - center_y) + center_x
                        sphero.target_y = (sphero.x - center_x) * (-1) + center_y
                    else: # Counterclockwise
                        sphero.target_x = (sphero.y - center_y) * (-1) + center_x
                        sphero.target_y = (sphero.x - center_x) + center_y

                    # fill in next_grid spots
                    self.next_grid[sphero.target_x][sphero.target_y] = sphero.id

                    # update prev direction, direction
                    sphero.update_direction(valid_move)

                    # Update box
                    group.box = rotated_box


        self.purge_grid(self.next_grid) # get rid of box placeholders for rotation
        # all groups are moved. only thing left to do is flip the grids to get ready for the next iteration.
        self.current_grid = self.next_grid.copy()
        self.next_grid = [ [0 for _ in range(self.grid_height)] for _ in range(self.grid_width)] 

    def find_group_move(self, group: BondedGroup)-> int:
        '''
        randomly select a translation or a rotation from group.valid_moves
        take out that option from the group.valid_moves
        check if it's valid 
            if it's translation, check by calling self.check_translation(move)
            else do some special stuff for checking rotation of the group
        if it is valid, 
            return the move direction
        if it isn't, 
            keep trying to find a valid move
        if we run out of valid_directions to try
            return 0 (don't move)
        '''
        #reset the group valid moves
        group.reset_valid_moves()

        while len(group.valid_moves) > 0:
            #print(group.valid_moves)
            cur_direction = random.choice(group.valid_moves)
            #print('chose: ', cur_direction)
            group.valid_moves.remove(cur_direction)

            if cur_direction <= 8: # if it's a translation, check
                valid_move = True
                for sphero in group.spheros:
                    if not self.check_translation(sphero, cur_direction):
                        valid_move = False
                
            else: # it's a rotation, check rotation validity
                valid_move = self.check_rotation(group, cur_direction)

            if valid_move:
                return cur_direction
        
        # no valid directions! don't move.
        return 0

    def check_translation(self, sphero: Sphero, move: int) -> bool:
        '''
        Only to be used for checking translations (moves 1-8)
        for each sphero in self.spheros, check if the move will:
            1. go out of bounds
            2. go where another sphero is in self.next_grid
        '''   
        # make sure it's a translation
        if move in position_change.keys():
            dx, dy = position_change[move]

            #print('sphero next position x:', sphero.x+dx, 'y:', sphero.y+dy, '\nalgorithm width and height: ', self.grid_width, self.grid_height)
            in_bounds = (MARGIN <= sphero.x + dx < self.grid_width - MARGIN and 
                        MARGIN <= sphero.y + dy < self.grid_height - MARGIN)

            target_node_id = 99999
            if in_bounds:
                target_node_id = self.next_grid[sphero.x + dx][sphero.y + dy]
                # if there is nothing on the target node, target_node_id will be 0.

            #print('target_node_id = ', target_node_id)
            no_collisions = (target_node_id == 0)
            #print(f'is {move} valid:  {in_bounds and }')
            #print(f'in_bounds  {in_bounds}')
            return in_bounds and no_collisions
        # check for a rotation
        else:
            assert False, 'Do not use this function to check rotational moves!'
    
    def check_rotation(self, group: BondedGroup, move: int) -> bool:
        '''
        Check if a rotation is valid
        '''
        center_x = group.find_sphero(group.center).x
        center_y = group.find_sphero(group.center).y
        rotated_box = group.rotate_box(group.box, move)

        # Check if entire box is in bounds
        # Not sure if this is correct with the coordinate system FIXME ALAN 
        in_bounds = (MARGIN <= center_x - rotated_box[3] and center_x + rotated_box[1] <= self.grid_width - MARGIN and 
                        MARGIN <= center_y - rotated_box[0] and center_y + rotated_box[2] <= self.grid_height - MARGIN)
        
        if in_bounds:

            # Check if entire box is unoccupied
            for x in range(group.find_sphero(group.center).x - rotated_box[3], group.find_sphero(group.center).x + rotated_box[1]):
                for y in range(group.find_sphero(group.center).y - rotated_box[2], group.find_sphero(group.center).y + rotated_box[0]):
                    if self.next_grid[x][y] != 0:
                        return False
                    
            return True
        
        else:
            return False



    def reset_sphero_positions(self) -> None:
        '''
        for each sphero, set its x and y to its target_x and target_y values. 
        this simulates 'moving' the sphero to its target.
        '''
        for group in self.bonded_groups:
            for sphero in group.spheros:
                sphero.x = sphero.target_x
                sphero.y = sphero.target_y

   
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

    def purge_grid(self, grid):
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                if grid[x][y] == -1:
                    grid[x][y] = 0