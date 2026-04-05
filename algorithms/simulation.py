import pygame
from .constants import constants
from .algorithm import Algorithm
from .sphero import Sphero
from math import hypot, atan, asin, cos, sin, pi

'''
 run the folllowing line to start the simulation:
 
                python -m algorithms.simulation

 '''

def draw_grid(surface):
    """
    Draw the grid lines

    Args:
        surface: (pygame.display) the pygame surface

    Returns:
        None
    """
    for x in range(0, constants.SIM_WIDTH, constants.SIM_DIST):
        pygame.draw.line(surface=surface, color=constants.BLACK, start_pos=(x, 0), end_pos=(x, constants.SIM_HEIGHT))
  
    for y in range(0, constants.SIM_HEIGHT, constants.SIM_DIST):
        pygame.draw.line(surface=surface, color=constants.BLACK, start_pos=(0, y), end_pos=(constants.SIM_WIDTH, y))
    
    for x in range(0, constants.SIM_WIDTH, constants.SIM_DIST):
        for y in range(0, constants.SIM_HEIGHT, constants.SIM_DIST):
            pygame.draw.line(surface, constants.BLACK, (x, y), (x + constants.SIM_DIST, y + constants.SIM_DIST))
            pygame.draw.line(surface, constants.BLACK, (x + constants.SIM_DIST, y), (x, y + constants.SIM_DIST))
    
def draw_pause_button(surface, color, rect, paused):
    pygame.draw.rect(surface, color, rect)
    font = pygame.font.Font(None, 36)
    button_name = 'Pause'
    if (paused == True):
        button_name = 'Resume'
    text = font.render(button_name, True, constants.BLACK)
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

    if (abs(sphero.target_x - sphero.x) <= constants.EPSILON and
        abs(sphero.target_y - sphero.y) <= constants.EPSILON):
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
        sphero.true_x = sphero.target_x
        sphero.true_y = sphero.target_y
        return False
    
    

    if sphero.direction <= 8:
        # print(f"Direction: {sphero.direction}\tx pos change: {position_change[sphero.direction][0]}")
        sphero.x += constants.position_change[sphero.direction][0] * (sphero.speed / constants.SIM_DIST)
        sphero.y += constants.position_change[sphero.direction][1] * (sphero.speed / constants.SIM_DIST)
    elif not constants.ARC_ROTATION:
        # move sphero straight to its target for a rotation
        # I'm lazily using true_x and true_y to hold the sphero's previous location.
        dx = sphero.target_x - sphero.true_x
        dy = sphero.target_y - sphero.true_y
        sphero.x += dx * (sphero.speed / constants.SIM_DIST)
        sphero.y += dy * (sphero.speed / constants.SIM_DIST)
    else:
        step_length = (sphero.speed / constants.SIM_DIST)

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
    sphero.true_x = sphero.target_x
    sphero.true_y = sphero.target_y

def draw_sphero(surface, sphero):
    """
    Draw the sphero in pygame

    Args:
        surface: (pygame.display) the pygame surface
        sphero: (Sphero) our passed in sphero

    Returns:
        None
    """
    pygame.draw.circle(surface, sphero.color, (sphero.x * constants.SIM_DIST, sphero.y * constants.SIM_DIST), constants.SPHERO_SIM_RADIUS)

spheros = []

if __name__ == "__main__":
    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode((constants.SIM_WIDTH, constants.SIM_HEIGHT))
    pygame.display.set_caption("sphero-swarm simulation")

##### Generate N_SPHEROS spheros with head/tail traits ##########################
    initial_positions = constants.INITIAL_POSITIONS
    assert len(initial_positions) == constants.N_SPHEROS, 'Number of initial positions does not match N_SPHEROS'
    assert len(initial_positions) == len(set(initial_positions)), 'Cannot have repeats in initial_positions'
    assert len(constants.INITIAL_TRAITS) == constants.N_SPHEROS, 'INITIAL_TRAITS length must match N_SPHEROS'

    algorithm_spheros = []
    spheros = [] # put the Linked Spheros in here

    id = 1
    for (x, y), trait in zip(initial_positions, constants.INITIAL_TRAITS):
        algorithm_spheros.append(Sphero(id=id, x=x, y=y, trait=trait))
        id += 1

    algorithm = Algorithm(grid_width=constants.GRID_WIDTH,
                            grid_height=constants.GRID_HEIGHT,
                            spheros=algorithm_spheros)
    for sphero in algorithm_spheros:
       spheros.append(sphero)
    
    running = True
    step = 0
    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        surface.fill(constants.WHITE) # replace frame with empty background
        draw_grid(surface=surface)

        spheros_reached_target = True
        for sphero in spheros:
            if moving_sphero_to_target(sphero=sphero):
                spheros_reached_target = False 


        # if all spheros reached their target, bond spheros and find new directions
        if spheros_reached_target:

            step += 1
            algorithm.log(f"\n\tStep {step}\n")

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

    algorithm.log('END SIMULATION')
    with open(LOG_PATH, 'w') as log_file:
        log_file.writelines(algorithm.log_lines)
        print(f'\nLog written to {LOG_PATH}\n')

def StartSimulation(algorithm):
    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode((constants.SIM_WIDTH, constants.SIM_HEIGHT))
    pygame.display.set_caption("sphero-swarm simulation")


    algorithm_spheros = algorithm.find_all_spheros()
    for sphero in algorithm_spheros:
        spheros.append(sphero)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        surface.fill(constants.WHITE) # replace frame with empty background
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