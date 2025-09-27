import math

class Sphero:
    def __init__(self, id, x, y, 
                 previous_direction, direction):
        self.id = id
        self.x = x
        self.y = y
        self.previous_direction = previous_direction
        self.direction = direction

    def update_direction(self, direction):
        self.previous_direction = self.direction
        self.direction = direction

    def get_direction_change(self):
        return self.previous_direction - self.direction

    # checks whether spheros are one node apart
    def can_bond(self, adj_sphero):
        if (math.abs(self.x - adj_sphero.x) <= 1 and
            math.abs(self.y - adj_sphero.y) <= 1):
            return True
        return False


    def __str__(self):
        return f"{self.id}"