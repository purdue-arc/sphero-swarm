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


    def find_all_spheros(self) -> list[Sphero]:
        '''
        returns list of all spheros contained in our grid algorithm
        '''
        spheros = []
        for group in self.bonded_groups:
            for sphero in group.spheros:
                spheros.append(sphero)
        return spheros

    def bond_all_groups(self) -> None:
        '''
        bonds any groups in bonded_groups whose spheros bond with each other according to their bonding rules.
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
                    #print('in bounds, neighbor_spheros exist')

                    # the neighboring sphero belongs to another group; we have to bond
                    if neighbor_sphero.group_id != sphero.group_id:
                        #print(f'bond {sphero} with {neighbor_sphero}')
                        self.bond_two_groups(sphero.group_id, neighbor_sphero.group_id)
    
    def bond_two_groups(self, group_1_id, group_2_id) -> None:
        '''
        gives all of group 2's spheros to group 1
        '''
        # print('bonding ', group_1_id, group_2_id)
        group_1 = self.find_group(group_1_id)
        group_2 = self.find_group(group_2_id)
        assert group_1 and group_2, 'should be valid group ids passed into bond_two_groups!!!'

        for sphero in group_2.spheros:

            # put in group 1
            group_1.spheros.append(sphero)

            # TODO update bonding rules if necessary

        # update spheros group_id in group 1
        group_1.update_sphero_membership()

        # reset everything in group 2. this is not really necessary since we remove group_2 from the list
        # group_2.spheros = []
        # group_2.size = -1
        # group_2.box = [0,0,0,0]
        # group_2.center = -1
        self.bonded_groups.remove(group_2)
    
    def find_sphero(self, id: int) -> Sphero | None:
        '''
        returns Sphero whose id matches in the passed in id
        else -1
        '''
        for group in self.bonded_groups:
            for sphero in group.spheros:
                if sphero.id == id:
                    return sphero
        return None
    
    def find_group(self, id: int) -> BondedGroup | None:
        '''
        returns BondedGroup whose group_id matches in the passed in id
        else -1
        '''
        for group in self.bonded_groups:
            if group.group_id == id:
                return group
        return None

    def move_all_groups(self) -> None:
        '''
        for each group: 
            finds a valid move
            updates all attributes within the group and within the spheros
           
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

                print(f"Group: {group.group_id}\tDirection: {valid_move}\tTranslation")

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

                print(f"Group: {group.group_id}\tDirection: {valid_move}\tRotation")

                center = self.find_sphero(group.center)

                # Calculate the area to block
                center_x = center.x
                center_y = center.y
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
                    print(f'Target_x = {sphero.target_x}\tTarget_y = {sphero.target_y}')
                    self.next_grid[sphero.target_x][sphero.target_y] = sphero.id

                    # update prev direction, direction
                    sphero.update_direction(valid_move)

                    # Update box
                    group.box = rotated_box


        self.purge_grid(self.next_grid) # get rid of box placeholders for rotation
        # all groups are moved. only thing left to do is flip the grids to get ready for the next iteration.
        self.current_grid = self.next_grid.copy()
        self.next_grid = [ [0 for _ in range(self.grid_height)] for _ in range(self.grid_width)] 

    def find_group_move(self, group: BondedGroup) -> int:
        '''
        given a group, finds a valid move for it and returns it.
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
        Check if a rotation is valid for the group
        '''
        center_x = group.find_sphero(group.center).x
        center_y = group.find_sphero(group.center).y
        rotated_box = group.rotate_box(group.box, move)

        up_bound = center_y + rotated_box[0] + 1
        right_bound = center_x + rotated_box[1] + 1
        down_bound = center_y - rotated_box[2] - 1
        left_bound = center_x - rotated_box[3] - 1

        # Check if entire box is in bounds
        # Not sure if this is correct with the coordinate system FIXME ALAN 
        in_bounds = (MARGIN <= left_bound and right_bound < self.grid_width - MARGIN and 
                        MARGIN <= down_bound and up_bound < self.grid_height - MARGIN)
        
        if in_bounds:

            # Check if entire box is unoccupied
            for x in range(left_bound, right_bound):
                for y in range(down_bound, up_bound):
                    print(f'Checking ({x}, {y})')
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

    def purge_grid(self, grid) -> None:
        '''
        removes all -1 values from a grid.

        helper function for rotation collision checking
        '''
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                if grid[x][y] == -1:
                    grid[x][y] = 0