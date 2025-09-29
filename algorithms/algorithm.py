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

        if not initial_positions:
            initial_positions = self.generate_random_grid()

        if not colors:
            colors = self.generate_random_colors()

        id = 1
        # initial_positions.sort(key=lambda pos: (pos[0], pos[1]))
        for (x, y), color in zip(initial_positions, colors):
            self.spheros[id - 1] = Sphero(id=id, x=x, y=y, color=color, direction=0)
            self.nodes[x][y] = id
            id += 1
        self.swarm = Swarm(n=n_spheros)

    def generate_random_colors(self):
        colors = []
        for _ in range(self.n_spheros):
            colors.append(random.choice(COLORS))
        return colors

    def generate_random_grid(self):
        positions = []
        for _ in range(self.n_spheros):
            x, y = self.random_initial_position()
            positions.append((x, y))
        return positions

    def random_initial_position(self): # -> (int, int)
        x = random.randint(MARGIN, self.grid_width - MARGIN)
        y = random.randint(MARGIN, self.grid_height - MARGIN)
        while self.nodes[x][y]:
            x = random.randint(MARGIN, self.grid_width - MARGIN)
            y = random.randint(MARGIN, self.grid_height - MARGIN)

        # Reserve the node with a sentinel (e.g., -1) so subsequent picks
        # know it's taken; real IDs will be written in __init__ assignment.
        self.nodes[x][y] = -1
        return x, y

    def find_sphero(self, id): # -> Sphero
        return self.spheros[id - 1]

    def in_bounds(self, x, y):
        return MARGIN <= x < GRID_WIDTH - MARGIN and MARGIN <= y < GRID_HEIGHT - MARGIN
    
    def is_valid_move(self, direction, sphero): # -> bool
        id = sphero.id
        target_x, target_y = sphero.compute_target_position(direction=direction)
        if not self.in_bounds(target_x, target_y):
            return False
        return (not self.nodes[target_x][target_y] or
                self.swarm.is_bonded(id1=id, id2=self.nodes[target_x][target_y]))

    def find_valid_move(self, sphero, possible_directions): # -> (int, array[int])
        direction = random.choice(possible_directions)
        while not self.is_valid_move(direction=direction, sphero=sphero) and possible_directions:
            possible_directions.remove(direction)
            if not possible_directions:
                return (0, [])
            direction = random.choice(possible_directions)
        return (direction, possible_directions) if possible_directions else (0, [])
    
    def find_bonded_group_move(self, bonded_group): # -> (int, array[int])
        possible_directions = [1, 2, 3, 4, 5, 6, 7, 8]
        direction = None
        for id in bonded_group:
            sphero = self.find_sphero(id)
            direction, possible_directions = self.find_valid_move(sphero=sphero,
                                                                  possible_directions=possible_directions)
            if not possible_directions:
                return (0, [])
        return direction, possible_directions
    
    def update_nodes(self, sphero):
        self.nodes[sphero.x][sphero.y] = 0
        self.nodes[sphero.target_x][sphero.target_y] = sphero.id
    
    def update_bonded_group_move(self, bonded_group):
        direction, possible_directions = self.find_bonded_group_move(bonded_group=bonded_group)
        for id in bonded_group:
            sphero = self.find_sphero(id)
            sphero.update_movement(direction=direction)
            self.update_nodes(sphero=sphero)
  
    def update_grid_move(self):
        for bonded_group in self.swarm.bonded_groups:
            self.update_bonded_group_move(bonded_group=bonded_group)

    def update_sphero_bonds(self, sphero):
        for direction in range(1, DIRECTIONS + 1):
            adj_x, adj_y = sphero.compute_target_position(direction=direction)
            if 0 < adj_x < GRID_WIDTH and 0 < adj_y < GRID_HEIGHT:
                adj_id = self.nodes[adj_x][adj_y]
                adj_sphero = self.find_sphero(id=adj_id)
                if sphero.can_bond(adj_sphero=adj_sphero):
                    self.swarm.combine(id1=sphero.id, id2=adj_id)
    
    def update_grid_bonds(self):
        for sphero in self.spheros:
            self.update_sphero_bonds(sphero=sphero)