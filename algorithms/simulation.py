import pygame
import constants
import random
import math
from algorithm import Algorithm

'''
    def update(self):

        # if the speed is 0, then we have stopped and no updating needs to happen
        if self.velocity_x == self.velocity_y == 0:
            return False

        # finds the distance to the target
        dx = abs(self.target_x - self.x)
        dy = abs(self.target_y - self.y)


        # if we get close enough of the target, we lock the ball's position
        if dx + dy < EPSILON:

            # lock to the target position. This will help avoid movement 
            # errors accumulating up over time.
            self.x = self.target_x
            self.y = self.target_y

            # also set the speed to 0 to show that the ball has stopped.
            self.velocity_x = 0
            self.velocity_y = 0
        else:
            self.x += self.velocity_x
            self.y += self.velocity_y

        return True

    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), SPHERO_RADIUS)

    def update_target(self):
        self.target_x = self.x + self.velocity_x * (TRIANGLE_SIZE) / 2
        self.target_y = self.y + self.velocity_y * (TRIANGLE_SIZE) / 2
'''

def draw_grid(surface):
    for x in range(0, constants.WIDTH, constants.NODES_DISTANCE):
        pygame.draw.line(surface=surface, color=constants.BLACK, start_pos=(x, 0), end_pos=(x, constants.HEIGHT))
  
    for y in range(0, constants.HEIGHT, constants.NODES_DISTANCE):
        pygame.draw.line(surface=surface, color=constants.BLACK, start_pos=(0, y), end_pos=(constants.WIDTH, y))
    
    for x in range (0, constants.WIDTH, constants.NODES_DISTANCE):
        for y in range(0, constants.HEIGHT, constants.NODES_DISTANCE):
            pygame.draw.line(surface=surface, color=constants.BLACK, start_pos=(x, y), end_pos=(x + constants.NODES_DISTANCE, y + constants.NODES_DISTANCE))
            pygame.draw.line(surface=surface, color=constants.BLACK, start_pos=(x + constants.NODES_DISTANCE, y), end_pos=(x, y + constants.NODES_DISTANCE))


def print_bonds(swarm):
    for bonded_group in swarm.bonded_groups:
        print(bonded_group) 
    
    
def draw_pause_button(surface, color, rect, paused):
    pygame.draw.rect(surface, color, rect)
    font = pygame.font.Font(None, 36)
    button_name = 'Pause'
    if (paused == True):
        button_name = 'Resume'
    text = font.render(button_name, True, constants.BLACK)
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)

def draw_rotate_button(surface, color):
    rect = pygame.Rect(10, 10, 100, 40)  # Positioned near the top-left corner
    pygame.draw.rect(surface, color, rect)
    
    font = pygame.font.Font(None, 36)
    button_name = 'Rotate'
    
    text = font.render(button_name, True, constants.BLACK)
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
    

if __name__ == "__main__":
    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode((constants.WIDTH, constants.HEIGHT))
    pygame.display.set_caption("sphero-swarm simulation")


    sphero_movement = Algorithm(width=constants.NODES_WIDTH,
                                height=constants.NODES_HEIGHT,
                                n_spheros=constants.N_SPHEROS)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # set to constant Background Color
        surface.fill(constants.WHITE)
        draw_grid(surface=surface)

        sphero_movement.update_grid_bonds()
        sphero_movement.update_grid_move()

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
