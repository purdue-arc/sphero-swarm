import random

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

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.nodes = [ [False] * width] * height

    def compute_target_position(self, position, direction):
        return (position + self.position_change[direction][0], position + self.position_change[1])
    
    def valid_move(self, direction, position):
        target_position = compute_target_position() 
        if target_x < 0 or target_x > self.width:
            return False
        if target_y < 0 or target_y > self.height:
            return False
        return self.nodes[target_x][target_y]

    def find_valid_move(self, x, y):
        possible_directions = [1, 2, 3, 4, 5, 6, 7, 8]
        
        direction = random.choice(possible_directions)
        while not self.valid_move(direction, x, y) and possible_directions:
            possible_directions.remove(direction)
            direction = random.choice(possible_directions)
        return direction if possible_directions else 0        