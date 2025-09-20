import math
import pygame

# Triangle settings
TRIANGLE_SIZE = 50  # Length of a side of each triangle
TRIANGLE_HEIGHT = 50 * math.sqrt(3)  # Height of a triangle

# Screen dimensions
WIDTH, HEIGHT = 800, 800

# Colors 
BACKGROUND_COLOR = (30, 30, 30)
LINE_COLOR = (200, 200, 200)
color = (200, 200, 200)

# CONSTS
SPHERO_RADIUS = 10


pygame.init()

class SpheroSim:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sphero Sparm Sim")
        print('initted')
    # Function to draw a triangular grid
    def draw_triangular_grid(self):
        # Fill the screen with the background color
        self.screen.fill(BACKGROUND_COLOR)

        # Draw the triangular grid
        #draw_triangular_grid(screen, TRIANGLE_SIZE, LINE_COLOR)
        triangle_size = TRIANGLE_SIZE
        triangle_size *= 2
        height = math.sqrt(3) / 2 * triangle_size  # Height of an equilateral triangle

        for y in range(-int(height), HEIGHT + int(height), int(height)):
            for x in range(0, WIDTH + triangle_size, triangle_size):
                # Calculate points for the upward triangle
                p1 = (x, y)
                p2 = (x + triangle_size // 2, y + int(height))
                p3 = (x - triangle_size // 2, y + int(height))

                # Draw the upward triangle
                pygame.draw.polygon(self.screen, color, [p1, p2, p3], 1)

                # draw the second triangle
                p11 = (x, y + int(height)//2)
                p22 = (x + triangle_size // 2, y + int(height)//2)
                p33 = (x - triangle_size // 2, y + int(height)//2)

                # Draw the upward triangle
                pygame.draw.polygon(self.screen, color, [p11, p22, p33], 1)

                # Calculate points for the downward triangle
                if y + int(2 * height) <= HEIGHT + int(height):
                    p4 = (x, y + int(2 * height))
                    pygame.draw.polygon(self.screen, color, [p2, p4, p3], 1)
    def draw_spheros(self, spheros):
        for sphero in spheros:
            pygame.draw.circle(self.screen, color, (int(sphero.x), int(sphero.y)), SPHERO_RADIUS)

    def flip(self):
        # Update the display
        pygame.display.flip()

    def quit(self):
        pygame.quit()

if __name__ == '__main__':
    simmy = SpheroSim()

