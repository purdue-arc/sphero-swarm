import pygame
from .constants import *
from .algorithm import Algorithm
from .sphero import Sphero, LinkedSphero
from math import hypot, atan, asin, cos, sin, pi

# run with python -m algorithms.simulation

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
    
    for x in range(0, SIM_WIDTH, SIM_DIST):
        for y in range(0, SIM_HEIGHT, SIM_DIST):
            pygame.draw.line(surface, BLACK, (x, y), (x + SIM_DIST, y + SIM_DIST))
            pygame.draw.line(surface, BLACK, (x + SIM_DIST, y), (x, y + SIM_DIST))
    
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
    if sphero.direction <= 8:
        # print(f"Direction: {sphero.direction}\tx pos change: {position_change[sphero.direction][0]}")
        sphero.x += position_change[sphero.direction][0] * (sphero.speed / SIM_DIST)
        sphero.y += position_change[sphero.direction][1] * (sphero.speed / SIM_DIST)
    else:
        
        

        step_length = (sphero.speed / SIM_DIST)

        center = algorithm.find_sphero(algorithm.find_group(sphero.group_id).center)
        dx_center = sphero.x - center.x
        dy_center = sphero.y - center.y
        dist_center = hypot(dx_center, dy_center)

        # Attempted solution, currently doesn't work
        # TODO: Try to fix this solution
        # if sphero is not center:
        #     if dx_center != 0:
        #         current_angle = atan(dy_center / dx_center)
        #     else:
        #         current_angle = (pi / 2) * (dy_center / abs(dy_center))

        #     delta_angle = asin(step_length / (2 * dist_center))

        #     if sphero.direction == 9:
        #         middle_angle = current_angle - delta_angle
        #         heading_x = -sin(middle_angle)
        #         heading_y = cos(middle_angle)
        #     else:
        #         middle_angle = current_angle + delta_angle
        #         heading_x = sin(middle_angle)
        #         heading_y = -cos(middle_angle)

        
        # else:
        #     ux = 0
        #     uy = 0



        # This version spins, but doesn't stop
        ux = dx_center / dist_center
        uy = dy_center / dist_center

        if sphero.direction == 9:
            heading_x = -uy
            heading_y = ux
        else:
            heading_x = uy
            heading_y = -ux

        sphero.x += heading_x * dist_center * step_length
        sphero.y += heading_y * dist_center * step_length


    return True

def teleport_sphero_to_target(sphero):
    """
    Teleport the sphero to the target position

    Args:
        sphero: (Sphero) our passed in sphero
    """
    sphero.x = sphero.target_x
    sphero.y = sphero.target_y

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

spheros = []

if __name__ == "__main__":
    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode((SIM_WIDTH, SIM_HEIGHT))
    pygame.display.set_caption("sphero-swarm simulation")

##### Generate N_SPHEROS random spheros #########################################
    initial_positions = INITIAL_POSITIONS
    assert len(initial_positions) == N_SPHEROS, 'Number of initial positions does not match N_SPHEROS'
    assert len(initial_positions) == len(set(initial_positions)), 'Cannot have repeats in initial_positions'

    # generate random colors for spheros
    colors = []
    for i in range(N_SPHEROS):
        colors.append(COLORS[i % len(COLORS)])
 
    # generate random initial positions if none passed in

    algorithm_spheros = []
    spheros = [] # put the Linked Spheros in here

    id = 1
    for (x, y), color in zip(initial_positions, colors):
        algorithm_spheros.append(Sphero(id=id, x=x, y=y, color=color))
        id += 1

    algorithm = Algorithm(grid_width=GRID_WIDTH,
                            grid_height=GRID_HEIGHT,
                            spheros=algorithm_spheros)
    for sphero in algorithm_spheros:
       spheros.append(LinkedSphero(sphero))
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        surface.fill(WHITE) # replace frame with empty background
        draw_grid(surface=surface)

        spheros_reached_target = True
        for sphero in spheros:
            if moving_sphero_to_target(sphero=sphero):
                spheros_reached_target = False 


        # if all spheros reached their target, bond spheros and find new directions
        if spheros_reached_target:
            # update sphero positions to simulate they reached their target
            algorithm.reset_sphero_positions()

            # bond
            algorithm.bond_all_groups()  # formerly used algorithm.update_grid_bonds()
            #print(str(algorithm))

            # move
            algorithm.move_all_groups() # formerly used algorithm.update_grid_move()
        
        # Draw the spheros
        for sphero in spheros:
            draw_sphero(surface=surface, sphero=sphero)

        # Update the display
        pygame.display.flip()

        # Control frame rate
        clock.tick(60)

def StartSimulation(algorithm):
    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode((SIM_WIDTH, SIM_HEIGHT))
    pygame.display.set_caption("sphero-swarm simulation")

    for sphero in algorithm.spheros:
        spheros.append(LinkedSphero(sphero))
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        surface.fill(WHITE) # replace frame with empty background
        draw_grid(surface=surface)

        for sphero in spheros:
            moving_sphero_to_target(sphero=sphero)

        # Draw the spheros
        for sphero in spheros:
            draw_sphero(surface=surface, sphero=sphero)
            # print(sphero)

        # Update the display
        pygame.display.flip()

        # Control frame rate
        clock.tick(60)