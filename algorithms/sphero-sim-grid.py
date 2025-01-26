import pygame
import math

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Triangular Grid")

# Colors
BACKGROUND_COLOR = (30, 30, 30)
LINE_COLOR = (200, 200, 200)

# Triangle settings
TRIANGLE_SIZE = 40  # Length of a side of each triangle

# Function to draw a triangular grid
def draw_triangular_grid(surface, triangle_size, color):
    height = math.sqrt(3) / 2 * triangle_size  # Height of an equilateral triangle

    for y in range(0, HEIGHT, int(height)):
        for x in range(0, WIDTH, triangle_size):
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
            if y + int(2 * height) < HEIGHT:
                p4 = (x, y + int(2 * height))
                pygame.draw.polygon(surface, color, [p2, p4, p3], 1)

if __name__ == "__main__":
    # Main loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Fill the screen with the background color
        screen.fill(BACKGROUND_COLOR)

        # Draw the triangular grid
        draw_triangular_grid(screen, TRIANGLE_SIZE, LINE_COLOR)

        # Update the display
        pygame.display.flip()

    # Quit Pygame
    pygame.quit()
