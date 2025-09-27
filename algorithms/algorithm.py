import random
from constants import MARGIN, DIRECTIONS
from algorithms.swarm import Swarm
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

    def __init__(self, node_width, node_height, n_spheros, initial_positions=None):
        self.node_width = node_width
        self.node_height = node_height
        self.nodes = [ [0 for _ in range(node_width)] for _ in range(node_height)]
        self.n_spheros = n_spheros
        self.spheros = [None] * n_spheros
        id = 1

        if not initial_positions:
            self.generate_random_grid()

        for x, y in initial_positions:
            self.spheros.append(Sphero(id=id, x=x, y=y, direction=0))
            self.nodes[x][y] = id
            id += 1
        self.swarm = Swarm(n=n_spheros)

    def generate_random_grid(self):
        for id in (1, self.n_spheros + 1):
            self.random_initial_position(id=id)

    def random_initial_position(self, id): # -> (int, int)
        x = random.randint(0, self.node_width - 1)
        y = random.randint(0, self.node_height - 1)
        while self.nodes[x][y]:
            x = random.randint(0, self.node_width - 1)
            y = random.randint(0, self.node_height - 1)
        self.nodes[x][y] = id
        return x, y

    def find_sphero(self, id): # -> Sphero
        return self.spheros[id]

    def compute_target_position(self, sphero, direction): # -> (int, int)
        return (sphero.x + self.position_change[direction][0], sphero.y + self.position_change[direction][1])
    
    def is_valid_move(self, direction, sphero, id): # -> bool
        target_x, target_y = self.compute_target_position(direction=direction, sphero=sphero)
        if target_x < MARGIN or target_x >= self.node_width - MARGIN:
            return False
        if target_y < MARGIN or target_y >= self.node_height - MARGIN:
            return False
        return (not self.nodes[target_x][target_y] or
                self.swarm.is_bonded(id1=id, id2=self.nodes[target_x][target_y]))

    # direction or movement or move?
    def find_valid_move(self, sphero, possible_directions): # -> (int, array[int])
        direction = random.choice(possible_directions)
        while not self.is_valid_move(direction=direction, sphero=sphero) and possible_directions:
            possible_directions.remove(direction)
            direction = random.choice(possible_directions)
        return (direction, possible_directions) if possible_directions else (0, [])
    

    # movement?
    def find_bonded_group_move(self, bonded_group): # -> (int, array[int])
        possible_directions = [1, 2, 3, 4, 5, 6, 7, 8]
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
    

    # movement?
    def update_bonded_group_move(self, bonded_group):
        direction, possible_directions = self.find_bonded_group_move(bonded_group=bonded_group)
        for id in bonded_group:
            sphero = self.find_sphero(id)
            sphero.update_direction(direction=direction)
            self.update_nodes(sphero=sphero, direction=direction)

    # update_grid_movement instead ??    
    def update_grid_move(self):
        for bonded_group in self.swarm.bonded_groups:
            self.update_bonded_group_move(bonded_group=bonded_group)
    

    # find a better function name
    def check_bonding(self, sphero):
        # think about making directions constant or not
        for direction in range(1, DIRECTIONS + 1):
            adj_x, adj_y = self.compute_target_position(sphero=sphero, direction=direction)
            adj_id = self.nodes[adj_x][adj_y]
            adj_sphero = self.find_sphero(id=adj_id)
            if sphero.can_bond(adj_sphero=adj_sphero):
                self.swarm.combine(id1=sphero.id, id2=adj_id)