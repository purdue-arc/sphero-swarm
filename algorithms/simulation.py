import pygame
from constants import *
from algorithm import Algorithm

def draw_grid(surface):
    """
    Draw the grid lines

    Args:
        surface: (pygame.display) the pygame surface

    Returns:
        None
    """
    for x in range(0, SIM_WIDTH, SIM_DIST):
        pygame.draw.line(surface=surface, color=BLACK, start_pos=(x, 0), end_pos=(x, SIM_HEIGHT))
  
    for y in range(0, SIM_HEIGHT, SIM_DIST):
        pygame.draw.line(surface=surface, color=BLACK, start_pos=(0, y), end_pos=(SIM_WIDTH, y))
    
    for x in range (0, SIM_WIDTH, SIM_DIST):
        for y in range(0, SIM_HEIGHT, SIM_DIST):
            pygame.draw.line(surface=surface, color=BLACK, start_pos=(x, y), end_pos=(x + SIM_DIST, y + SIM_DIST))
            pygame.draw.line(surface=surface, color=BLACK, start_pos=(x + SIM_DIST, y), end_pos=(x, y + SIM_DIST))
    
    
def draw_pause_button(surface, color, rect, paused):
    pygame.draw.rect(surface, color, rect)
    font = pygame.font.Font(None, 36)
    button_name = 'Pause'
    if (paused == True):
        button_name = 'Resume'
    text = font.render(button_name, True, BLACK)
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)
    
def reached_target(sphero):
    """
    Did the sphero reach their target positions

    Args:
        sphero: (Sphero) our passed in sphero

    Returns:
        (bool): Did the sphero reach it's target position?
    """

    if (abs(sphero.target_x - sphero.x) <= EPSILON and
        abs(sphero.target_y - sphero.y) <= EPSILON):
        return True
    return False

def moving_sphero_to_target(sphero):
    """
    Move the sphero to the target position

    Args:
        sphero: (Sphero) our passed in sphero

    Returns:
        (bool): Did the Sphero reach it's target
    """
    if reached_target(sphero=sphero):
        sphero.x = sphero.target_x
        sphero.y = sphero.target_y
        return False
    sphero.x += position_change[sphero.direction][0] * (sphero.speed / SIM_DIST)
    sphero.y += position_change[sphero.direction][1] * (sphero.speed / SIM_DIST)
    return True

def draw_sphero(surface, sphero):
    """
    Draw the sphero in pygame

    Args:
        surface: (pygame.display) the pygame surface
        sphero: (Sphero) our passed in sphero

    Returns:
        None
    """
    pygame.draw.circle(surface, sphero.color, (sphero.x * SIM_DIST, sphero.y * SIM_DIST), SPHERO_SIM_RADIUS)

if __name__ == "__main__":
    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode((SIM_WIDTH, SIM_HEIGHT))
    pygame.display.set_caption("sphero-swarm simulation")


    algorithm = Algorithm(grid_width=GRID_WIDTH,
                            grid_height=GRID_HEIGHT,
                            n_spheros=N_SPHEROS)
    for sphero in algorithm.spheros:
        print(sphero)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        surface.fill(WHITE) # replace frame with empty background
        draw_grid(surface=surface)

        spheros_reached_target = True
        for sphero in algorithm.spheros:
            if moving_sphero_to_target(sphero=sphero):
                spheros_reached_target = False 


        # if all spheros reached their target, bond spheros and find new directions
        if spheros_reached_target:
            algorithm.update_grid_bonds()
            algorithm.update_grid_move()
        
        # Draw the spheros
        for sphero in algorithm.spheros:
            draw_sphero(surface=surface, sphero=sphero)
            print(sphero)

        # Update the display
        pygame.display.flip()

        # Control frame rate
        clock.tick(60)