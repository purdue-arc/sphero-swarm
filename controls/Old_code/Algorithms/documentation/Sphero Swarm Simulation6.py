import pygame
import math

# Constants for the simulation
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

# Pygame initialization
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Sphero Swarm Simulation with Color Change")
font = pygame.font.SysFont(None, 24)


# Button class for the UI
class Button:
    def __init__(self, x, y, width, height, text, color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.clicked = False
        self.action = action

    def draw(self, screen, font):
        pygame.draw.rect(screen, self.color, self.rect)
        text_surface = font.render(self.text, True, BLACK)
        screen.blit(text_surface, (self.rect.x + 10, self.rect.y + 10))

    def check_click(self, pos):
        if self.rect.collidepoint(pos):
            if self.action:
                self.action()
            return True
        return False


# Sphero class definition
class Sphero:
    def __init__(self, id, position, velocity, acceleration):
        self.id = id
        self.position = position  # [x, y]
        self.velocity = velocity  # [vx, vy]
        self.acceleration = acceleration  # [ax, ay]
        self.color = BLUE

    def update_position(self, dt):
        self.position[0] += self.velocity[0] * dt * 100  # Scaling to make movement visible
        self.position[1] += self.velocity[1] * dt * 100  # Scaling to make movement visible

        # Handle bouncing off the walls (reverse velocity on contact with the wall)
        if self.position[0] - SPHERO_RADIUS < 0 or self.position[0] + SPHERO_RADIUS > SCREEN_WIDTH:
            self.velocity[0] = -self.velocity[0]

        if self.position[1] - SPHERO_RADIUS < 0 or self.position[1] + SPHERO_RADIUS > SCREEN_HEIGHT:
            self.velocity[1] = -self.velocity[1]

    def update_velocity(self, dt):
        ax, ay = self.acceleration
        new_velocity_x = self.velocity[0] + ax * dt
        new_velocity_y = self.velocity[1] + ay * dt

        # Limit velocity to maximum speed
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
        # Calculate the normal vector between the two Spheros
        dx = other.position[0] - self.position[0]
        dy = other.position[1] - self.position[1]
        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance == 0:
            # Avoid division by zero by slightly offsetting one Sphero
            distance = 0.1

        # Normal vector (direction of collision)
        nx = dx / distance
        ny = dy / distance

        # Tangent vector (perpendicular to the normal vector)
        tx = -ny
        ty = nx

        # Dot product of velocity in the normal direction
        v1n = self.velocity[0] * nx + self.velocity[1] * ny
        v1t = self.velocity[0] * tx + self.velocity[1] * ty
        v2n = other.velocity[0] * nx + other.velocity[1] * ny
        v2t = other.velocity[0] * tx + other.velocity[1] * ty

        # Since the collision is elastic, we swap the normal velocities
        v1n_new = v2n
        v2n_new = v1n

        # Update velocities with the new normal and unchanged tangential velocities
        self.velocity[0] = v1n_new * nx + v1t * tx
        self.velocity[1] = v1n_new * ny + v1t * ty
        other.velocity[0] = v2n_new * nx + v2t * tx
        other.velocity[1] = v2n_new * ny + v2t * ty

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


# SpheroSwarm class to manage the swarm
class SpheroSwarm:
    def __init__(self, num_spheros):
        self.spheros = []
        self.selected_sphero = None

        # Hardcoded velocity and acceleration values for each Sphero
        initial_data = [
            {"position": [100, 100], "velocity": [1, 0.5], "acceleration": [0.1, 0.05]},
            {"position": [200, 200], "velocity": [-1, 0.3], "acceleration": [-0.1, 0.02]},
            {"position": [300, 300], "velocity": [0.5, -1], "acceleration": [0.05, -0.1]},
            {"position": [400, 400], "velocity": [0.2, 0.8], "acceleration": [0.02, 0.08]},
            {"position": [500, 100], "velocity": [-0.7, -0.5], "acceleration": [-0.07, -0.05]},
            {"position": [600, 500], "velocity": [1, -0.2], "acceleration": [0.1, -0.02]},
            {"position": [700, 300], "velocity": [-0.5, 0.9], "acceleration": [-0.05, 0.09]},
            {"position": [100, 400], "velocity": [0.3, -0.6], "acceleration": [0.03, -0.06]},
            {"position": [200, 500], "velocity": [-0.9, 0.4], "acceleration": [-0.09, 0.04]},
            {"position": [300, 200], "velocity": [0.6, -0.3], "acceleration": [0.06, -0.03]},
        ]

        for i in range(num_spheros):
            data = initial_data[i]
            self.spheros.append(Sphero(i, data["position"], data["velocity"], data["acceleration"]))

    def update(self, dt):
        for sphero in self.spheros:
            sphero.update_position(dt)
            sphero.update_velocity(dt)
            for other in self.spheros:
                if sphero != other:
                    sphero.check_collision(other)

    def draw(self, screen):
        for sphero in self.spheros:
            sphero.draw(screen)

    def select_sphero(self, pos):
        for sphero in self.spheros:
            distance = math.sqrt((sphero.position[0] - pos[0]) ** 2 + (sphero.position[1] - pos[1]) ** 2)
            if distance <= SPHERO_RADIUS:
                self.selected_sphero = sphero
                return

    def change_selected_sphero_color(self, color):
        if self.selected_sphero:
            self.selected_sphero.color = color

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

    # Define color change buttons
    buttons = [
        Button(10, 10, 100, 40, "Red", RED, lambda: swarm.change_selected_sphero_color(RED)),
        Button(120, 10, 100, 40, "Blue", BLUE, lambda: swarm.change_selected_sphero_color(BLUE)),
        Button(230, 10, 100, 40, "Black", BLACK, lambda: swarm.change_selected_sphero_color(BLACK)),
        Button(10, 60, 200, 40, "Show Raw Data", GRAY, None),  # Button to toggle raw data display
    ]

    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS
        screen.fill(WHITE)  # Clear the screen to white

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                for button in buttons:
                    if button.check_click(pos):
                        if button.text == "Show Raw Data":
                            show_data = not show_data  # Toggle display of raw data
                swarm.select_sphero(pos)  # Select the Sphero on click

        swarm.update(dt)
        swarm.draw(screen)

        # Draw the buttons
        for button in buttons:
            button.draw(screen, font)

        # Show raw data if the button is clicked
        if show_data:
            raw_data = swarm.display_raw_data()
            for i, data in enumerate(raw_data):
                text_surface = font.render(data, True, BLACK)
                screen.blit(text_surface, (10, 110 + i * 20))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run_simulation()
