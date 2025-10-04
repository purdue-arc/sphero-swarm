import random
from constants import *
from swarm import Swarm
from sphero import Sphero

class Algorithm:
    def __init__(self, grid_width, grid_height, n_spheros,
                 colors=None, initial_positions=None):
        
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.nodes = [ [0 for _ in range(grid_width)] for _ in range(grid_height)]
        self.n_spheros = n_spheros
        self.spheros = [None for _ in range(n_spheros)]

        # generate random initial positions if none passed in
        if not initial_positions:
            initial_positions = self.generate_random_grid()

        # generate random colors for spheros if none passed in
        if not colors:
            colors = self.generate_random_colors()

        id = 1
        for (x, y), color in zip(initial_positions, colors):
            self.spheros[id - 1] = Sphero(id=id, x=x, y=y, color=color, direction=0)
            self.nodes[x][y] = id
            id += 1
        self.swarm = Swarm(n=n_spheros)

    def generate_random_colors(self):
        """
        Generate an array of random colors of size number of spheros

        Args:
            None

        Returns:
            List[colors]: a list of random colors, with length equal to number of spheros
        """

        colors = []
        for _ in range(self.n_spheros):
            colors.append(random.choice(COLORS))
        return colors

    def random_initial_position(self): # -> (int, int)
        """
        Generate a valid random initial position on the grid

        Args:
            None

        Returns:
            (int, int): a valid random initial position
        """

        x = random.randint(MARGIN, self.grid_width - MARGIN)
        y = random.randint(MARGIN, self.grid_height - MARGIN)
        while self.nodes[x][y]:
            x = random.randint(MARGIN, self.grid_width - MARGIN)
            y = random.randint(MARGIN, self.grid_height - MARGIN)
        return x, y

    def generate_random_grid(self):
        """
        Generate a random set of initial positions for all spheros on the grid

        Args:
            None
        
        Returns:
            List[int]: a list of random intiial positions, with length equal to the number of spheros
        """

        positions = []
        for _ in range(self.n_spheros):
            x, y = self.random_initial_position()
            positions.append((x, y))
        return positions

    def find_sphero(self, id): # -> Sphero
        """
        The sphero object that has the specified id

        Args:
            id: (int) the sphero's id
        
        Returns:
            (Sphero): the sphero object that has the specified id
        """

        return self.spheros[id - 1]

    def in_bounds(self, x, y): # -> bool
        """
        Determins if the passed in position is in the grid bounds

        Args:
            x: (int) passed in x-coordinate 
            y: (int) passed in y-coordinate

        Returns:
            (bool): Is the x and y coordinates in the boundaries of the grid?
        """

        return MARGIN <= x < self.grid_width - MARGIN and MARGIN <= y < self.grid_height - MARGIN
    
    def is_valid_move(self, direction, sphero): # -> bool
        """
        Determine if the direction passed in is a valid direction for the sphero

        Args:
            direction: (int) value between 0 to DIRECTIONS
            sphero: (Sphero) the passed in sphero
        
        Returns:
            (bool): Is the direction passed in is a valid direction for the sphero?
        """

        id = sphero.id
        target_x, target_y = sphero.compute_target_position(direction=direction)
        if not self.in_bounds(target_x, target_y):
            return False
        return (not self.nodes[target_x][target_y] or
                self.swarm.is_bonded(id1=id, id2=self.nodes[target_x][target_y]))

    def find_valid_move(self, sphero, possible_directions): # -> List[int]
        """
        Find a valid direction for a sphero given a list of possible directions

        Args:
            sphero: (Sphero) the passed in sphero
            possible_directions: (List[int]) a list of possible directions

        Returns:
            (List[int]): a list of all valid directions for the given sphero
        """

        for direction in possible_directions[:]:
            if not self.is_valid_move(direction=direction, sphero=sphero):
                possible_directions.remove(direction)
        return possible_directions if possible_directions else []
    
    def find_bonded_group_move(self, bonded_group): # -> int
        """
        Find a valid direction for the bonded group

        Args:
            bonded_group: (List[int]) an array of sphero ids apart of the same bonded group

        Returns:
            (int): a valid direction for the bonded group
        """

        possible_directions = [1, 2, 3, 4, 5, 6, 7, 8]
        direction = None
        for id in bonded_group:
            sphero = self.find_sphero(id)
            possible_directions = self.find_valid_move(sphero=sphero,
                                                        possible_directions=possible_directions)
        direction = random.choice(possible_directions)
        return direction
    
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
            sphero.update_movement(direction=direction)
            self.update_nodes(sphero=sphero)
  
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
                adj_sphero = self.find_sphero(id=adj_id)

                # bond both spheros if they can bond
                if sphero.can_bond(adj_sphero=adj_sphero):
                    self.swarm.combine(id1=sphero.id, id2=adj_id)
    
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
