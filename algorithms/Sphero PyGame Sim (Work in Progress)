import pygame
import random
import math

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Sphero Swarm Simulation')

# Colors
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)

# Sphero properties
NUM_SPHEROS = 10
RADIUS = 15
MAX_SPEED = 5

class Sphero:
    def __init__(self, x=None, y=None, radius=RADIUS, speed=None, angle=None):
        self.x = x if x is not None else random.randint(RADIUS, WIDTH - RADIUS)
        self.y = y if y is not None else random.randint(RADIUS, HEIGHT - RADIUS)
        self.radius = radius
        self.angle = angle if angle is not None else random.uniform(0, 2 * math.pi)
        self.speed = speed if speed is not None else random.uniform(1, MAX_SPEED)

    def move(self):
        # Update position based on speed and angle
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

        # Bounce off walls
        if self.x - self.radius <= 0 or self.x + self.radius >= WIDTH:
            self.angle = math.pi - self.angle
        if self.y - self.radius <= 0 or self.y + self.radius >= HEIGHT:
            self.angle = -self.angle

    def draw(self):
        pygame.draw.circle(screen, BLUE, (int(self.x), int(self.y)), self.radius)

    def collide(self, other):
        # Check for collision with another sphero
        dx = self.x - other.x
        dy = self.y - other.y
        distance = math.hypot(dx, dy)

        if distance < self.radius + other.radius:
            return True
        return False

    def merge(self, other):
        # Merge properties of two spheros
        new_x = (self.x + other.x) / 2
        new_y = (self.y + other.y) / 2
        new_radius = self.radius + other.radius

        # Calculate new speed and angle (average for simplicity)
        new_speed = (self.speed + other.speed) / 2
        new_angle = (self.angle + other.angle) / 2

        return Sphero(new_x, new_y, new_radius, new_speed, new_angle)

# Create sphero swarm
spheros = [Sphero() for _ in range(NUM_SPHEROS)]

# Main loop
running = True
clock = pygame.time.Clock()

while running:
    screen.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Check for collisions and merge spheros
    merged_indices = set()
    new_spheros = []

    for i, sphero in enumerate(spheros):
        if i in merged_indices:
            continue  # Skip already merged spheros

        for j, other in enumerate(spheros[i + 1:], start=i + 1):
            if j in merged_indices:
                continue  # Skip already merged spheros

            if sphero.collide(other):
                merged_sphero = sphero.merge(other)
                new_spheros.append(merged_sphero)
                merged_indices.update([i, j])
                break
        else:
            # Only move and draw if not merged
            sphero.move()
            sphero.draw()

    # Add newly merged spheros to the swarm
    spheros = [s for i, s in enumerate(spheros) if i not in merged_indices] + new_spheros

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
