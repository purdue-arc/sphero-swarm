import math

class Sphero:
    def __init__(self, id, x, y, velocity_x, velocity_y, color):
        self.id = id
        self.x = x
        self.y = y
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.color = color

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

    def update_direction(self, direction):

        # move right
        if (direction == 1):
            self.velocity_x = 2
            self.velocity_y = 0

        # move up right
        elif (direction == 2):
            self.velocity_x = 1
            self.velocity_y = (math.sqrt(3))

        # move up left
        elif (direction == 3):
            self.velocity_x = -1
            self.velocity_y = (math.sqrt(3))

        # move left
        elif (direction == 4):
            self.velocity_x = -2
            self.velocity_y = 0

        # move down left
        elif (direction == 5):
            self.velocity_x = -1
            self.velocity_y = -(math.sqrt(3)) 

        # move down right
        elif (direction == 6):
            self.velocity_x = 1
            self.velocity_y = -(math.sqrt(3)) 
    
    def rotate(self, angle):
        # do sum
        print("rotate")

    def update_target(self):
        self.target_x = self.x + self.velocity_x * (TRIANGLE_SIZE) / 2
        self.target_y = self.y + self.velocity_y * (TRIANGLE_SIZE) / 2


    # checks whether spheros are one grid space apart
    def check_bonding(self, other):
        distance = math.sqrt((self.x - other.x) ** 2 +
                             (self.y - other.y) ** 2)
        if (distance <= TRIANGLE_SIZE + EPSILON):
            return True
        return False

    def __str__(self):
        return f"{self.id}"