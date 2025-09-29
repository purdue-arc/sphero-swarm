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
    sphero.x += position_change[sphero.direction][0] * sphero.speed
    sphero.y += position_change[sphero.direction][1] * sphero.speed
    return True

def draw_sphero(surface, sphero):
    pygame.draw.circle(surface, sphero.color, (int(sphero.x) * SIM_DIST, int(sphero.y) * SIM_DIST), SPHERO_SIM_RADIUS)

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
            print(sphero)

        if spheros_reached_target:
            algorithm.update_grid_bonds()
            algorithm.update_grid_move()
        
        # Draw the spheros
        for sphero in algorithm.spheros:
            draw_sphero(surface=surface, sphero=sphero)

        # Update the display
        pygame.display.flip()

        # Control frame rate
        clock.tick(3)
        



'''
if __name__ == "__main__":

    # Initialize Pygame
    pygame.init()
    # clock 
    clock = pygame.time.Clock()

    screen = pygame.display.set_mode((constants.WIDTH, constants.HEIGHT))
    pygame.display.set_caption("sphero-swarm simulation")

    #instantiate spheros
    spheros = []
    colors = [RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE]

    # number of spheros
    N_SPHEROS = 20

    # The bonds array is a 2D array that stores a set of individual 1D arrays which contain all spheros bonded that are bonded together
    # EX: Sphero 1 and 2 are bonded together, whereas Sphero 3 is bonded with no one which would be stored as such:
    # bonds = [[1, 2], [3]]

    # Initially all spheros are bonded to "themselves", so each sphero has their own 1D array

    bonds = []
    coords = set()

    #instantiating all spheros
    index = 0
    while len(spheros) < N_SPHEROS:
        # randomly generate X coordinate by generating a random triangle on the grid 
        # and multiplying it by the size of a triangle to recieve it's exact pixel value
        x = random.randint(2, WIDTH // (TRIANGLE_SIZE*2) * 2 - 2) * (TRIANGLE_SIZE)

        # repeat process for y except with height of traingle rather than width
        y = random.randint(2, int(HEIGHT // TRIANGLE_HEIGHT - 1)) * TRIANGLE_HEIGHT
        if (x, y) not in coords:
            spheros.append(Sphero(index, x, y, x, y, 0, 0, colors[index % len(colors)]))        
            bonds.append([spheros[index]])
            coords.add((x, y))
            index+=1
    
    pause_button_rect = pygame.Rect(WIDTH - 100, 10, 100, 40)


    paused = False

    # Main loop
    running = True
    while running:
        rotate_button_rect = draw_rotate_button(screen, WHITE)
        # waits until someone exits the game, then quits
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if pause_button_rect.collidepoint(event.pos):
                    paused = not paused
                elif rotate_button_rect.collidepoint(event.pos):  # Check if the "Rotate" button is clicked
                    # print("rotate", bonds)
                    print_bonds(bonds)

        if not paused:
            # Fill the screen with the background color
            screen.fill(BACKGROUND_COLOR)

            # Draw the triangular grid
            draw_triangular_grid(screen, TRIANGLE_SIZE, LINE_COLOR)


            # Update the position of all spheros to get closer to their target value
            # If all Spheros have reached their target "updated" will be False
            updated = False
            for sphero in spheros:
                if sphero.update():
                    updated = True

            # If all of the Spheros have reached their target they have all stopped moving
            # Now that they have stopped moving choose a new random direction for them to travel in and check bonding

            if not updated:

                # update bonding
                i = 0           
                while (i < len(bonds)):
                    j = 0
                    while (j < len(bonds[i])):
                        sphero = bonds[i][j]
                        k = i + 1
                        while(k < len(bonds)):
                            l = 0
                            while (l < len(bonds[k])):
                                other = bonds[k][l]
                                # if two spheros are a SET distance apart, bond them
                                      collision = True
                                        # this direction doesn't work, so remove it
                                        available_directions.pop(current_direction)

                                        # since removing we are shifting the list, we need to adjust the current direction
                                        if (current_direction >= len(available_directions)):
                                            current_direction = 0
                                        
                                        sphero.update_direction(available_directions[current_direction])
                                        sphero.update_target()

                                    else:
                                        found_direction = True
                        
                    # reupdate all spheros to make sure they are all moving the same direction
                    if (collision == True):
                        # go through all the spheros in the bonding group and update their direction
                        for j in range(len(bonds[i])):
                            sphero = bonds[i][j]
                    
                            if (len(available_directions) != 0):
                                sphero.update_direction(available_directions[current_direction])
                                
                            # if no available directions exist, then just stop moving
                            else:
                                sphero.velocity_x = 0
                                sphero.velocity_y = 0  
                            sphero.update_target() # When bonding we combine their two individual arrays into one
                                if (sphero.check_bonding(other)):
                                    bonds[i].extend(bonds[k])
                                    bonds.pop(k)
                                    k -= 1
                                    break
                                l += 1
                            k += 1
                        j += 1
                    i += 1

                # update direction
                # i goes through each bonding group
                for i in range(len(bonds)):

                    # generate new direction
                    direction = random.randint(1, 6)

                    # update the spheros in the bonding groups direction and target
                    # j goes through each sphero in the selected bonding group
                    for j in range(len(bonds[i])):
                        sphero = bonds[i][j]
                        sphero.update_direction(direction)
                        sphero.update_target()

                    # IDEA:
                    #   check all other previous bonding group's spheros target_x and target_y with our own sphero's target_x and target_y
                    #   if there is a potential collision that means the direction we had previously chosen is invalid, thus remove it from
                    #   the list of available directions. Once we have gone through all spheros and checked if they will collide with a previous
                    #   sphero we simply choose a direction from the remaining list and reupdate the all of the sphero's directions in the bonding group
                    
                    #   If absolutely no available direction exists then just stay in place for this cycle

                    # CODE:
                    available_directions = [1, 2, 3, 4, 5, 6] # list of possible movement direction
                    current_direction = direction - 1 # index of the current direction
                    collision = False # collision flag

                    # Iterate through all spheros in the current bond group
                    for j in range(len(bonds[i])):

                        sphero = bonds[i][j]
                        sphero.update_direction(available_directions[current_direction])
                        sphero.update_target()

                        # check out of bounds for first bonding group
                        if (i == 0):
                            found_direction = False
                            while (found_direction == False):

                                # if any sphero is out of bounds find a new direction
                                error = False
                                if (sphero.target_x - SPHERO_RADIUS < EPSILON or sphero.target_x - SPHERO_RADIUS + EPSILON > WIDTH):
                                    error = True
                                if (sphero.target_y - SPHERO_RADIUS < EPSILON or sphero.target_y - SPHERO_RADIUS + EPSILON > HEIGHT):
                                    error = True
                                
                                if (error == True):
                                    collision = True
                                    # this direction doesn't work, so remove it
                                    available_directions.pop(current_direction)

                                    # since removing we are shifting the list, we need to adjust the current direction
                                    if (current_direction >= len(available_directions)):
                                        current_direction = 0
                                    
                                    sphero.update_direction(available_directions[current_direction])
                                    sphero.update_target()

                                else:
                                    found_direction = True

                        #check all previous bonding groups for potential collisions
                        for k in range(i):
                            for l in range(len(bonds[k])):
                                other = bonds[k][l]

                                found_direction = False
                                while (found_direction == False):

                                    # if two spheros' x and y coordinates are close enough to each other (not exactly the same, but within a threshhold) 
                                    # or if they are out of bounds then change the direction
                                    error = False
                                    if (abs(other.target_x - sphero.target_x) <= EPSILON and abs(other.target_y - sphero.target_y) <= EPSILON):
                                        error = True
                                    if (sphero.target_x - SPHERO_RADIUS < EPSILON or sphero.target_x - SPHERO_RADIUS + EPSILON > WIDTH):
                                        error = True
                                    if (sphero.target_y - SPHERO_RADIUS < EPSILON or sphero.target_y - SPHERO_RADIUS + EPSILON > HEIGHT):
                                        error = True
                                    
                                    if (error == True):
                                 
        
        # Draw the pause button
        draw_pause_button(screen, WHITE, pause_button_rect, paused)
        draw_rotate_button(screen, WHITE)

        # Draw the spheros
        for sphero in spheros:
            sphero.draw()

        # Update the display
        pygame.display.flip()

        # Control frame rate
        clock.tick(60)

    # Quit Pygame
    pygame.quit()

'''
