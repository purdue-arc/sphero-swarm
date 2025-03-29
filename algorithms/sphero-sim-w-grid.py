import pygame
import math
import random 

# Initialize Pygame
pygame.init()
# clock 
clock = pygame.time.Clock()

# Screen dimensions
WIDTH, HEIGHT = 400, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sphero Sparm Sim")

# Constants 
SPHERO_RADIUS = 10
MAX_VELOCITY = 1
COLLISION_RADIUS = SPHERO_RADIUS
EPSILON = 8 # the amount of error we allow while detecting distance

# Colors 
BACKGROUND_COLOR = (30, 30, 30)
LINE_COLOR = (200, 200, 200)

BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)


# Triangle settings
TRIANGLE_SIZE = 50  # Length of a side of each triangle
TRIANGLE_HEIGHT = 50 * math.sqrt(3)  # Height of a triangle

# Function to draw a triangular grid
def draw_triangular_grid(surface, triangle_size, color):
    triangle_size *= 2
    height = math.sqrt(3) / 2 * triangle_size  # Height of an equilateral triangle

    for y in range(-int(height), HEIGHT + int(height), int(height)):
        for x in range(0, WIDTH + triangle_size, triangle_size):
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
            if y + int(2 * height) <= HEIGHT + int(height):
                p4 = (x, y + int(2 * height))
                pygame.draw.polygon(surface, color, [p2, p4, p3], 1)

# Sphero new class definition
class Sphero:
    def __init__(self, x, y, target_x, target_y, velocity_x, velocity_y, color):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.color = color

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

    def update_direction(self, direction):

        # move right
        if (direction == 1):
            self.velocity_x = 2
            self.velocity_y = 0

        # move up right
        elif (direction == 2):
            self.velocity_x = 1
            self.velocity_y = (math.sqrt(3))

        # move up left
        elif (direction == 3):
            self.velocity_x = -1
            self.velocity_y = (math.sqrt(3))

        # move left
        elif (direction == 4):
            self.velocity_x = -2
            self.velocity_y = 0

        # move down left
        elif (direction == 5):
            self.velocity_x = -1
            self.velocity_y = -(math.sqrt(3)) 

        # move down right
        elif (direction == 6):
            self.velocity_x = 1
            self.velocity_y = -(math.sqrt(3)) 
    
    def rotate(self, angle):
        # do sum
        print("rotate")

    def update_target(self):
        self.target_x = self.x + self.velocity_x * (TRIANGLE_SIZE) / 2
        self.target_y = self.y + self.velocity_y * (TRIANGLE_SIZE) / 2


    # checks whether spheros are one grid space apart
    def check_bonding(self, other):
        distance = math.sqrt((self.x - other.x) ** 2 +
                             (self.y - other.y) ** 2)
        if (distance <= TRIANGLE_SIZE + EPSILON):
            return True
        return False

    def __str__(self):
        return (f"Ball(x={self.x}, y={self.y}, "
                f"target_x={self.target_x}, target_y={self.target_y}, "
                f"velocity_x={self.velocity_x}, velocity_y={self.velocity_y}, "
                f"color={self.color})")
    
# our pause button
def draw_pause_button(surface, color, rect, paused):
    pygame.draw.rect(surface, color, rect)
    font = pygame.font.Font(None, 36)
    button_name = 'Pause'
    if (paused == True):
        button_name = 'Resume'
    text = font.render(button_name, True, BLACK)
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)

# our pause button
def draw_rotate_button(surface, color, rect, paused):
    pygame.draw.rect(surface, color, rect)
    font = pygame.font.Font(None, 36)
    button_name = 'Rotate'
    # if (paused == True):
    #     button_name = 'Resume'
    text = font.render(button_name, True, BLACK)
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)

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

    #instantiate spheros
    spheros = []
    colors = [RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE]

    # number of spheros
    N = 2

    # The bonds array is a 2D array that stores a set of individual 1D arrays which contain all spheros bonded that are bonded together
    # EX: Sphero 1 and 2 are bonded together, whereas Sphero 3 is bonded with no one which would be stored as such:
    # bonds = [[1, 2], [3]]

    # Initially all spheros are bonded to "themselves", so each sphero has their own 1D array

    bonds = []
    coords = set()

    #instantiating all spheros
    index = 0
    while len(spheros) < N:
        # randomly generate X coordinate by generating a random triangle on the grid 
        # and multiplying it by the size of a triangle to recieve it's exact pixel value
        x = random.randint(2, WIDTH // (TRIANGLE_SIZE*2) * 2 - 2) * (TRIANGLE_SIZE)

        # repeat process for y except with height of traingle rather than width
        y = random.randint(2, int(HEIGHT // TRIANGLE_HEIGHT - 1)) * TRIANGLE_HEIGHT
        if (x, y) not in coords:
            spheros.append(Sphero(x, y, x, y, 0, 0, colors[index % len(colors)]))        
            bonds.append([spheros[index]])
            coords.add((x, y))
            index+=1
    
    pause_button_rect = pygame.Rect(WIDTH - 100, 10, 100, 40)


    paused = False

    # Main loop
    running = True
    while running:

        # waits until someone exits the game, then quits
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if pause_button_rect.collidepoint(event.pos):
                    paused = not paused

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
                                # When bonding we combine their two individual arrays into one
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
                            sphero.update_target()
        
        # Draw the pause button
        draw_pause_button(screen, WHITE, pause_button_rect, paused)
        draw_rotate_button(screen, WHITE, pause_button_rect, paused)

        # Draw the spheros
        for sphero in spheros:
            sphero.draw()

        # Update the display
        pygame.display.flip()

        # Control frame rate
        clock.tick(60)

    # Quit Pygame
    pygame.quit()
