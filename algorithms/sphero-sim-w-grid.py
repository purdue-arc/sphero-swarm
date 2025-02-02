import pygame
import math

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 1000, 1000
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sphero Sparm Sim")

# Colors
BACKGROUND_COLOR = (30, 30, 30)
LINE_COLOR = (200, 200, 200)

# Constants stole from sim 7
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SPHERO_RADIUS = 10
MAX_VELOCITY = 2
COLLISION_RADIUS = SPHERO_RADIUS


# Colors 
BLUE = (0, 0, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)


# Triangle settings
TRIANGLE_SIZE = 100  # Length of a side of each triangle

# Function to draw a triangular grid
def draw_triangular_grid(surface, triangle_size, color):
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
            self.position[0] -= 2 * velocity * dt;

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
        if (distance <= TRIANGLE_SIZE):
            # TODO handle bonding
            self.handle_bonding(other)

    def draw(self, screen):
         # Draw the Sphero as a circle
        pygame.draw.circle(screen, self.color, (int(self.position[0]), int(self.position[1])), SPHERO_RADIUS)


    #
    # def handle_collision(self, other):
    #     # Calculate the normal vector between the two Spheros
    #     dx = other.position[0] - self.position[0]
    #     dy = other.position[1] - self.position[1]
    #     distance = math.sqrt(dx ** 2 + dy ** 2)
    #
    #     if distance == 0:
    #         # Avoid division by zero by slightly offsetting one Sphero
    #         distance = 0.1
    #
    #     # Normal vector (direction of collision)
    #     nx = dx / distance
    #     ny = dy / distance
    #
    #     # Tangent vector (perpendicular to the normal vector)
    #     tx = -ny
    #     ty = nx
    #
    #     # Dot product of velocity in the normal direction
    #     v1n = self.velocity[0] * nx + self.velocity[1] * ny
    #     v1t = self.velocity[0] * tx + self.velocity[1] * ty
    #     v2n = other.velocity[0] * nx + other.velocity[1] * ny
    #     v2t = other.velocity[0] * tx + other.velocity[1] * ty
    #
    #     # Since the collision is elastic, we swap the normal velocities
    #     v1n_new = v2n
    #     v2n_new = v1n
    #
    #     # Update velocities with the new normal and unchanged tangential velocities
    #     self.velocity[0] = v1n_new * nx + v1t * tx
    #     self.velocity[1] = v1n_new * ny + v1t * ty
    #     other.velocity[0] = v2n_new * nx + v2t * tx
    #     other.velocity[1] = v2n_new * ny + v2t * ty
    #
    # def draw(self, screen):
    #     # Draw the Sphero as a circle
    #     pygame.draw.circle(screen, self.color, (int(self.position[0]), int(self.position[1])), SPHERO_RADIUS)
    #
    #     # Draw an arrow representing the velocity vector
    #     vx, vy = self.velocity
    #     arrow_length = 20  # Shorter line for the velocity
    #     end_x = self.position[0] + vx * arrow_length
    #     end_y = self.position[1] + vy * arrow_length
    #     pygame.draw.line(screen, BLACK, (int(self.position[0]), int(self.position[1])), (int(end_x), int(end_y)), 2)
    #
    #     # Draw arrowhead
    #     angle = math.atan2(vy, vx)
    #     arrowhead_length = 5
    #     pygame.draw.line(screen, BLACK, (int(end_x), int(end_y)),
    #                      (int(end_x - arrowhead_length * math.cos(angle - math.pi / 6)),
    #                       int(end_y - arrowhead_length * math.sin(angle - math.pi / 6))), 2)
    #     pygame.draw.line(screen, BLACK, (int(end_x), int(end_y)),
    #                      (int(end_x - arrowhead_length * math.cos(angle + math.pi / 6)),
    #                       int(end_y - arrowhead_length * math.sin(angle + math.pi / 6))), 2)
    #
    # def display_raw_data(self):
    #     return f"Sphero {self.id} | Pos: ({self.position[0]:.2f}, {self.position[1]:.2f}), " \
            #            f"Vel: ({self.velocity[0]:.2f}, {self.velocity[1]:.2f}), " \
            #            f"Acc: ({self.acceleration[0]:.2f}, {self.acceleration[1]:.2f})"
    #

if __name__ == "__main__":

    #instantiate spheros
    spheros = []

    sphero_1 = Sphero(1, [0,0], 1, BLUE)
    sphero_2 = Sphero(1, [0,0], 2, RED)
    spheros.append(sphero_1)
    spheros.append(sphero_2)

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
        for sphero in spheros:
            sphero.update_position(1)

        # Draw the spheros
        for sphero in spheros:
            sphero.draw(screen)

        # Update the display
        pygame.display.flip()

    # Quit Pygame
    pygame.quit()
