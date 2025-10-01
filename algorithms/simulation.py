import pygame
from constants import *
from algorithm import Algorithm

def draw_grid(surface):
    for x in range(0, SIM_WIDTH, SIM_DIST):
        pygame.draw.line(surface=surface, color=BLACK, start_pos=(x, 0), end_pos=(x, SIM_HEIGHT))
  
    for y in range(0, SIM_HEIGHT, SIM_DIST):
        pygame.draw.line(surface=surface, color=BLACK, start_pos=(0, y), end_pos=(SIM_WIDTH, y))
    
    for x in range (0, SIM_WIDTH, SIM_DIST):
        for y in range(0, SIM_HEIGHT, SIM_DIST):
            pygame.draw.line(surface=surface, color=BLACK, start_pos=(x, y), end_pos=(x + SIM_DIST, y + SIM_DIST))
            pygame.draw.line(surface=surface, color=BLACK, start_pos=(x + SIM_DIST, y), end_pos=(x, y + SIM_DIST))


def print_bonds(swarm):
    for bonded_group in swarm.bonded_groups:
        print(bonded_group) 
    
    
def draw_pause_button(surface, color, rect, paused):
    pygame.draw.rect(surface, color, rect)
    font = pygame.font.Font(None, 36)
    button_name = 'Pause'
    if (paused == True):
        button_name = 'Resume'
    text = font.render(button_name, True, BLACK)
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)

def draw_rotate_button(surface, color):
    rect = pygame.Rect(10, 10, 100, 40)  # Positioned near the top-left corner
    pygame.draw.rect(surface, color, rect)
    
    font = pygame.font.Font(None, 36)
    button_name = 'Rotate'
    
    text = font.render(button_name, True, BLACK)
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)
    
    return rect  # Returning rect for event handling
    '''
    So we need to implement rotation on a group
    find the mid point - and if the mid point is not an actual sphero coord then get the closest one.
    Choose this as the pivot everything else needs to rotate.
    The bond can rotate either clockwise or counterclockwise
    The further away a node is from the pivot, the faster it has to move to its desired spot

    add a speed parameter to modify the speed to which it goes.

    we need to pick a direction
    then calc if the destination of rotation is within bounds.
    if its not then DONT ROTATE IT
    '''
    
def reached_target(sphero):
    if (abs(sphero.target_x - sphero.x) <= EPSILON and
        abs(sphero.target_y - sphero.y) <= EPSILON):
        return True
    return False

def moving_sphero_to_target(sphero):
    if reached_target(sphero=sphero):
        sphero.x = sphero.target_x
        sphero.y = sphero.target_y
        return False
    sphero.x += position_change[sphero.direction][0] * (sphero.speed / SIM_DIST)
    sphero.y += position_change[sphero.direction][1] * (sphero.speed / SIM_DIST)
    return True

def draw_sphero(surface, sphero):
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

        # set to constant Background Color
        surface.fill(WHITE)
        draw_grid(surface=surface)

        spheros_reached_target = True
        for sphero in algorithm.spheros:
            if moving_sphero_to_target(sphero=sphero):
                spheros_reached_target = False 

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