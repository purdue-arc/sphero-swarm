import pygame
import math
import random 

# Initialize Pygame
pygame.init()

clock = pygame.time.Clock()

# Screen dimensions
WIDTH, HEIGHT = 1000, 1000 
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sphero Sparm Sim")

# Constants 
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SPHERO_RADIUS = 10
MAX_VELOCITY = 1
COLLISION_RADIUS = SPHERO_RADIUS
EPSILON = 8 # the amount of error we allow while detecting distance

# Colors 
BACKGROUND_COLOR = (30, 30, 30)
LINE_COLOR = (200, 200, 200)

BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)


# Triangle settings
TRIANGLE_SIZE = 50  # Length of a side of each triangle
TRIANGLE_HEIGHT = 50 * math.sqrt(3)  # Height of a triangle

# Function to draw a triangular grid
def draw_triangular_grid(surface, triangle_size, color):
    triangle_size *= 2
    height = math.sqrt(3) / 2 * triangle_size  # Height of an equilateral triangle

    for y in range(-int(height), HEIGHT + int(height), int(height)):
        for x in range(0, WIDTH + triangle_size, triangle_size):
            # Calculate points for the upward triangle
            p1 = (x, y)
            p2 = (x + triangle_size // 2, y + int(height))
            p3 = (x - triangle_size // 2, y + int(height))

            # Draw the upward triangle
            pygame.draw.polygon(surface, color, [p1, p2, p3], 1)

            # draw the second triangle
            p11 = (x, y + int(height)//2)
            p22 = (x + triangle_size // 2, y + int(height)//2)
            p33 = (x - triangle_size // 2, y + int(height)//2)

            # Draw the upward triangle
            pygame.draw.polygon(surface, color, [p11, p22, p33], 1)

            # Calculate points for the downward triangle
            if y + int(2 * height) <= HEIGHT + int(height):
                p4 = (x, y + int(2 * height))
                pygame.draw.polygon(surface, color, [p2, p4, p3], 1)

# Sphero new class definition
class Sphero_2:
    def __init__(self, x, y, target_x, target_y, speed_x, speed_y, color):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.color = color

    def update_color(self, new_color):
        self.color = new_color

    def get_color(self):
        return self.color

    def update(self):

        # if the speed is 0, then we have stopped and no updating needs to happen
        if self.speed_x == self.speed_y == 0:
            return False

        # finds the distance to the target
        dx = abs(self.target_x - self.x)
        dy = abs(self.target_y - self.y)
        # distance = abs(dx) + abs(dy)
        #distance = math.sqrt(dx**2 + dy**2)

        # if we are far from the target, then go towards it. 
        # if dx >= self.speed_x and dy >= self.speed_y:
        #     self.x += self.speed_x
        #     self.y += self.speed_y
        #
        # # if we get close enough of the target, we lock the ball's position
        NODE_DIST_THRESHOLD = 6
        if dx + dy < NODE_DIST_THRESHOLD:

            # lock to the target position. This will help avoid movement 
            # errors accumulating up over time.
            self.x = self.target_x
            self.y = self.target_y

            # also set the speed to 0 to show that the ball has stopped.
            self.speed_x = 0
            self.speed_y = 0
        else:
            self.x += self.speed_x
            self.y += self.speed_y

        return True

    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), SPHERO_RADIUS)

    def update_direction(self, direction):

        #mvoe right
        if (direction == 1):
            self.speed_x = 2
            self.speed_y = 0

        #move up right
        elif (direction == 2):
            self.speed_x = 1
            self.speed_y = (math.sqrt(3))

            # move up left
        elif (direction == 3):

            self.speed_x = -1
            self.speed_y = (math.sqrt(3))

            # move left
        elif (direction == 4):
            self.speed_x = -2
            self.speed_y = 0

            # move down left
        elif (direction == 5):
            self.speed_x = -1
            self.speed_y = -(math.sqrt(3)) 

            # move down right
        elif (direction == 6):
            self.speed_x = 1
            self.speed_y = -(math.sqrt(3)) 

    # TODO disjoint set implementation
    def check_bonding(self, other):
        distance = math.sqrt((self.x - other.x) ** 2 +
                             (self.y - other.y) ** 2)
        if (distance <= TRIANGLE_SIZE):
            return True
        return False

    # TODO some way to go from our coordinates to the actual ones

    def __str__(self):
        return (f"Ball(x={self.x}, y={self.y}, "
                f"target_x={self.target_x}, target_y={self.target_y}, "
                f"speed_x={self.speed_x}, speed_y={self.speed_y}, "
                f"color={self.color})")

# Sphero class definition
class Sphero:
    def __init__(self, id, position, direction, color):
        self.id = id
        self.position = position  # [x, y]
        self.direction = direction # A direction 1-6
        self.color = color
        self.velocity = MAX_VELOCITY

    def update_position(self, dt):
        #self.position[0] += self.velocity[0] * dt * 100  # Scaling to make movement visible
        #self.position[1] += self.velocity[1] * dt * 100  # Scaling to make movement visible

        direction = self.direction
        velocity = self.velocity

        #mvoe right
        if (direction == 1):
            self.position[0] += 2 * velocity

        #move up right
        elif (direction == 2):
            self.position[0] += velocity
            self.position[1] += (math.sqrt(3)) * velocity

            # move up left
        elif (direction == 3):
            self.position[0] -= velocity * dt
            self.position[1] += (math.sqrt(3)) * velocity

            # move left
        elif (direction == 4):
            self.position[0] -= 2 * velocity * dt

            # move down left
        elif (direction == 5):
            self.position[0] -= velocity * dt
            self.position[1] -= (math.sqrt(3)) * velocity

            # move down right
        elif (direction == 6):
            self.position[0] += velocity * dt
            self.position[1] -= (math.sqrt(3)) * velocity

        # Handle bouncing off the walls (reverse velocity on contact with the wall)
        # if self.position[0] - SPHERO_RADIUS < 0 or self.position[0] + SPHERO_RADIUS > SCREEN_WIDTH:
        #     self.velocity[0] = -self.velocity[0]
        #
        # if self.position[1] - SPHERO_RADIUS < 0 or self.position[1] + SPHERO_RADIUS > SCREEN_HEIGHT:
        #     self.velocity[1] = -self.velocity[1]
    # def check_collision(self, other):
    #     distance = math.sqrt((self.position[0] - other.position[0]) ** 2 +
    #                          (self.position[1] - other.position[1]) ** 2)
    #     if distance < 2 * COLLISION_RADIUS:
    #         self.handle_collision(other)
    #
    def handle_bonding(self, other):
        # TODO implement union find first
        print("")
        # update set membership
    def check_bonding(self, other):
        distance = math.sqrt((self.position[0] - other.position[0]) ** 2 +
                             (self.position[1] - other.position[1]) ** 2)
        if (distance <= TRIANGLE_SIZE + EPSILON):
            self.handle_bonding(other)

    def draw(self, screen):
         # Draw the Sphero as a circle
        pygame.draw.circle(screen, self.color, (int(self.position[0]), int(self.position[1])), SPHERO_RADIUS)

def find(union_find, i):
    if (union_find[i] != i):
        union_find[i] = find(union_find, union_find[i])
    return i

def update_parent(union_find, new_parent, j):
    if (union_find[j] != j):
        update_parent(union_find, new_parent, union_find[j])
    union_find[j] = new_parent
        


if __name__ == "__main__":

    #instantiate spheros
    spheros = []
    colors = []

    # here are some hard coded ones. 
    #sphero_1 = Sphero_2(4 * TRIANGLE_SIZE, 4*TRIANGLE_HEIGHT, 4 * TRIANGLE_SIZE, 4 * TRIANGLE_HEIGHT, 0, 0, RED)
    #sphero_2 = Sphero_2(3 * TRIANGLE_SIZE, 3*TRIANGLE_HEIGHT, 3 * TRIANGLE_SIZE, 3 * TRIANGLE_HEIGHT, 0, 0, RED)
    
    
    # spheros.append(sphero_1)
    # spheros.append(sphero_2)

    # TODO make a function that generates N random spheros with valid coordinates.
    N = 6
    bonds = []
    colors = [RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE]
    for i in range(N):
        x = random.randint(2, WIDTH // (TRIANGLE_SIZE*2) * 2 - 2) * (TRIANGLE_SIZE)
        print(x)
        y = random.randint(2, int(HEIGHT // TRIANGLE_HEIGHT - 1)) * TRIANGLE_HEIGHT
        spheros.append(Sphero_2(x, y, x, y, 0, 0, colors[i]))
        bonds.append([spheros[i]])

    # Main loop
    running = True
    while running:

        #waits until someone exits the game, then quits
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Fill the screen with the background color
        screen.fill(BACKGROUND_COLOR)

        # Draw the triangular grid
        draw_triangular_grid(screen, TRIANGLE_SIZE, LINE_COLOR)


        # Update the spheros
        updated = False
        for sphero in spheros:
            if sphero.update():
                updated = True

        # If none have been updated, then 
        # choose new directions for them to travel in.
        if not updated:
            #update bonding
            i = 0           
            while(i < len(bonds) ):
                print("i " + str(i))
                print("length of total bonds " + str(len(bonds)))
                print("length of bonds i" + str(len(bonds[i])))
                j = 0
                while (j < len(bonds[i])):
                    print("j " + str(j))
                    sphero = bonds[i][j]
                    k = i + 1
                    while(k < len(bonds)):
                        print("k " + str(k))
                        print("length of k bond " + str(len(bonds[k])))
                        l = 0
                        while (l < len(bonds[k])):
                            other = bonds[k][l]
                            if (sphero.check_bonding(other)):
                                bonds[i].extend(bonds[k])
                                bonds.pop(k)
                                k -= 1
                                break
                            l += 1
                        k += 1
                    j += 1
                i += 1

            #update direction
            for i in range(len(bonds)):
                direction = random.randint(1, 6)

                for j in range(len(bonds[i])):
                    sphero = bonds[i][j]
                    sphero.update_direction(direction)
                    sphero.target_x = sphero.x + sphero.speed_x * (TRIANGLE_SIZE) / 2
                    sphero.target_y = (sphero.y + sphero.speed_y * (TRIANGLE_SIZE) / 2)

        # Draw the spheros
        for sphero in spheros:
            sphero.draw()
            #print(sphero)

        # Update the display
        pygame.display.flip()

        # Control frame rate
        clock.tick(60)

    # Quit Pygame
    pygame.quit()
