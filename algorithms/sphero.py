import math

class Sphero:
    def __init__(self, id, x, y, previous_direction, direction):
        self.id = id
        self.x = x
        self.y = y
        self.target_x 
        self.target_y
        self.previous_direction = previous_direction
        self.direction = direction

    def update_direction(self, direction):
        self.previous_direction = self.direction
        self.direction = direction

    def update(self):

        # if the speed is 0, then we have stopped and no updating needs to happen
        if self.velocity_x == self.velocity_y == 0:
            return False

        # finds the distance to the target
        dx = abs(self.target_x - self.x)
        dy = abs(self.target_y - self.y)


        # if we get close enough of the target, we lock the ball's position
        if dx + dy < EPSILON:

            # lock to the target position. This will help avoid movement 
            # errors accumulating up over time.
            self.x = self.target_x
            self.y = self.target_y

            # also set the speed to 0 to show that the ball has stopped.
            self.velocity_x = 0
            self.velocity_y = 0
        else:
            self.x += self.velocity_x
            self.y += self.velocity_y

        return True

    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), SPHERO_RADIUS)

    def update_target(self):
        self.target_x = self.x + self.velocity_x * (TRIANGLE_SIZE) / 2
        self.target_y = self.y + self.velocity_y * (TRIANGLE_SIZE) / 2


    # checks whether spheros are one node apart
    def can_bond(self, adj_sphero):
        if (math.abs(self.x - adj_sphero.x) <= 1 and
            math.abs(self.y - adj_sphero.y) <= 1):
            return True
        return False


    def __str__(self):
        return f"{self.id}"