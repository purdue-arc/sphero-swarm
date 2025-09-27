import pygame
import constants




# Initialize Pygame
pygame.init()
# clock 
clock = pygame.time.Clock()

screen = pygame.display.set_mode((constants.WIDTH, constants.HEIGHT))
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # clear background
    screen.fill((255, 255, 255))

    # draw your grid
    draw_grid(screen)

    # update the screen
    pygame.display.flip()