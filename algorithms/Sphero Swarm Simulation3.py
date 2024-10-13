import pygame
import random
import math

# Constants for the simulation
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SPHERO_RADIUS = 10
MAX_ACCELERATION = 5
MAX_VELOCITY = 2
COLLISION_RADIUS = SPHERO_RADIUS

# Colors
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)

# Pygame initialization
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Sphero Swarm Simulation with Accelerometer Data")
font = pygame.font.SysFont(None, 24)


# Sphero class definition
class Sphero:
    def __init__(self, id, position, velocity, heading):
        self.id = id
        self.position = position  # [x, y]
        self.velocity = velocity  # [vx, vy]
        self.heading = heading  # angle in radians
        self.acceleration = [0, 0]  # [ax, ay]
        self.color = BLUE

    def update_position(self, dt):
        self.position[0] += self.velocity[0] * dt * 100  # Scaling to make movement visible
        self.position[1] += self.velocity[1] * dt * 100  # Scaling to make movement visible

        # Handle bouncing off the walls (reverse velocity on contact with the wall)
        if self.position[0] - SPHERO_RADIUS < 0 or self.position[0] + SPHERO_RADIUS > SCREEN_WIDTH:
            self.velocity[0] = -self.velocity[0]

        if self.position[1] - SPHERO_RADIUS < 0 or self.position[1] + SPHERO_RADIUS > SCREEN_HEIGHT:
            self.velocity[1] = -self.velocity[1]

    def update_velocity(self, acceleration, dt):
        ax, ay = acceleration
        new_velocity_x = self.velocity[0] + ax * dt
        new_velocity_y = self.velocity[1] + ay * dt

        # Update the accelerometer data
        self.acceleration = [ax, ay]

        speed = math.sqrt(new_velocity_x ** 2 + new_velocity_y ** 2)

        if speed > MAX_VELOCITY:
            factor = MAX_VELOCITY / speed
            new_velocity_x *= factor
            new_velocity_y *= factor

        self.velocity = [new_velocity_x, new_velocity_y]

    def check_collision(self, other):
        distance = math.sqrt((self.position[0] - other.position[0]) ** 2 +
                             (self.position[1] - other.position[1]) ** 2)
        if distance < 2 * COLLISION_RADIUS:
            self.handle_collision(other)

    def handle_collision(self, other):
        # Reverse velocities to simulate bounce when two Spheros collide
        self.velocity[0] = -self.velocity[0]
        self.velocity[1] = -self.velocity[1]
        other.velocity[0] = -other.velocity[0]
        other.velocity[1] = -other.velocity[1]
        # Indicate the collision by changing the color momentarily
        self.color = RED
        other.color = RED

    def draw(self, screen):
        # Draw the Sphero as a circle
        pygame.draw.circle(screen, self.color, (int(self.position[0]), int(self.position[1])), SPHERO_RADIUS)

        # Draw an arrow representing the velocity vector
        vx, vy = self.velocity
        arrow_length = 20  # Shorter line for the velocity
        end_x = self.position[0] + vx * arrow_length
        end_y = self.position[1] + vy * arrow_length
        pygame.draw.line(screen, BLACK, (int(self.position[0]), int(self.position[1])), (int(end_x), int(end_y)), 2)

        # Draw arrowhead
        angle = math.atan2(vy, vx)
        arrowhead_length = 5
        pygame.draw.line(screen, BLACK, (int(end_x), int(end_y)),
                         (int(end_x - arrowhead_length * math.cos(angle - math.pi / 6)),
                          int(end_y - arrowhead_length * math.sin(angle - math.pi / 6))), 2)
        pygame.draw.line(screen, BLACK, (int(end_x), int(end_y)),
                         (int(end_x - arrowhead_length * math.cos(angle + math.pi / 6)),
                          int(end_y - arrowhead_length * math.sin(angle + math.pi / 6))), 2)

    def display_raw_data(self):
        return f"Sphero {self.id} | Pos: ({self.position[0]:.2f}, {self.position[1]:.2f}), " \
               f"Vel: ({self.velocity[0]:.2f}, {self.velocity[1]:.2f}), " \
               f"Acc: ({self.acceleration[0]:.2f}, {self.acceleration[1]:.2f})"


# Polymerization Sphero Swarm class to manage the swarm
class SpheroSwarm:
    def __init__(self, num_spheros):
        self.spheros = []
        for i in range(num_spheros):
            position = [random.uniform(0, SCREEN_WIDTH), random.uniform(0, SCREEN_HEIGHT)]
            velocity = [random.uniform(-MAX_VELOCITY, MAX_VELOCITY), random.uniform(-MAX_VELOCITY, MAX_VELOCITY)]
            heading = random.uniform(0, 2 * math.pi)
            self.spheros.append(Sphero(i, position, velocity, heading))

    def update(self, dt):
        for sphero in self.spheros:
            sphero.update_position(dt)
            for other in self.spheros:
                if sphero != other:
                    sphero.check_collision(other)

    def control_spheros(self):
        for sphero in self.spheros:
            # Apply random acceleration to Spheros
            ax = random.uniform(-MAX_ACCELERATION, MAX_ACCELERATION)
            ay = random.uniform(-MAX_ACCELERATION, MAX_ACCELERATION)
            sphero.update_velocity([ax, ay], 0.1)

    def draw(self, screen):
        for sphero in self.spheros:
            sphero.draw(screen)

    def display_raw_data(self):
        raw_data = []
        for sphero in self.spheros:
            raw_data.append(sphero.display_raw_data())
        return raw_data


# Main function to run the simulation
def run_simulation():
    swarm = SpheroSwarm(num_spheros=10)
    clock = pygame.time.Clock()
    running = True
    show_data = False  # Flag to toggle raw data display
    button = Button(10, 10, 200, 40, "Show Raw Data")  # Button to toggle raw data display

    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS
        screen.fill(WHITE)  # Clear the screen to white

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button.check_click(event.pos):
                    show_data = not show_data  # Toggle display of raw data

        swarm.update(dt)
        swarm.control_spheros()
        swarm.draw(screen)

        # Draw the button
        button.draw(screen, font)

        # Show raw data if the button is clicked
        if show_data:
            raw_data = swarm.display_raw_data()
            for i, data in enumerate(raw_data):
                text_surface = font.render(data, True, BLACK)
                screen.blit(text_surface, (10, 60 + i * 20))

        pygame.display.flip()

    pygame.quit()


# Button class
class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = GRAY
        self.clicked = False

    def draw(self, screen, font):
        pygame.draw.rect(screen, self.color, self.rect)
        text_surface = font.render(self.text, True, BLACK)
        screen.blit(text_surface, (self.rect.x + 10, self.rect.y + 10))

    def check_click(self, pos):
        if self.rect.collidepoint(pos):
            self.clicked = not self.clicked
            return True
        return False


if __name__ == "__main__":
    run_simulation()
