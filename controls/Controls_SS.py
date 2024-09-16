from spherov2 import scanner  # Scanner to find and connect to Sphero Robots
from spherov2.sphero_edu import SpheroEduAPI  # Import the API to control Sphero Edu robots
from spherov2.types import Color  # Import the Color class to set LED colors
import multiprocessing  # Import multiprocessing for process-based parallelism (not used here)
import threading  # Import threading for thread-based parallelism **
import time  # Import time for sleep and other time-related functions
import sys  # Import sys for system-specific functions (e.g., exit)


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def toy_manager(toy, id):
    global commands  # Access the global commands list
    with SpheroEduAPI(toy) as api:  # Open a connection to the Sphero toy
        while True:  # Infinite loop to keep managing commands
            print(id)  # Print the toy ID for debugging
            
            global allReady  # Access the global allReady list
            global commands  # Access the global commands list

            choosenColor = Color(r = 0, g = 0, b = 0)  # Initialize the color to black
            
            magBase = 0  # Initialize the base compass direction
            direction = 0  # Initialize the current direction
            numIterations = 0  # Initialize the iteration counter

            # Mega while loop that will keep taking enteries from the keyboard to execute until "%" is entered
            while True and commands[id] != []:  # Process commands if the command list is not empty, ensures that the commands list is empty
                print("{}: {}".format(id, commands[id][0]))  # Print the current command for debugging, printf concept, commands[id][0]= list of lists 
                                                             #the commands[0] is reffered to down near the end of the code 
                if (commands[id][0] == "%"):  # Exit the loop if the command is "%", % is the end of the command list, executes the rest of the list preceding it than ends
                    return
                
                elif (commands[id][0] == "c"):  # Calibrate the compass, c
                    api.calibrate_compass() # uses api to calibrate compass
                    magBase = api.get_compass_direction()  # Update the base direction
                    api.set_main_led(choosenColor)  # Set the LED color



                    # idea for speed in distance, if distance input = 11ft, 11-6.56 = 4.44 (ft in interval [2,inf)) set time = 2, 4.44/6.56 = 0.67, add to time counter. time = 2.67
                    # DISCLAIMER all calulations done are with guessed number, have to replace with real measurments we take 
                    # on interval [0,2) avg speed = 3.28 ft/s
                    # on interval [2,inf) avg speed = 6.56 ft/s

                elif(commands[id][0][0]== "M"):
                    distance = float(commands[id][1:])  # Convert command substring to float
                    time = 0.0  # Initialize time variable with float value
                    accDistance = 6.56 # sets the estimated distance per second
                    if (distance<accDistance): # checks if distance is less than AccDistance which is the estimated build up speed for 2 seconds
                        time = (2 * distance/ accDistance) # if distance is equivilent to less than 2 seconds, take 2 times distance divided by AccDistance which = 2 seconds in this time frame [0,2)
                    elif (distance > accDistance): # if distance is more than 2 seconds, which is the estimated build up time
                        time = ((distance - accDistance) / accDistance) + 2 # distance-AccDistance = time after 2 second build up to max speed, than divide that by the speed per second and add 2 because of the 2 build up seconds
                    api.roll(magBase + direction, 255, time) # api.roll causes the robot to move, magBase + direction = defines final direction the sphereo will move
                    time.sleep(0.5) # Wait for half a second after movement is made 

                

                elif (commands[id][0][0] == "m"):  # Move command, 2 [0][0] becasue we need 2 conditions for this m0.25, move 0.25 seconds
                    api.roll(magBase + direction, 255, float(commands[id][0][1:]))  # api.roll causes the robot to move, magBase + direction = defines final direction the sphereo will move
                                                                                    # if no direction adjustments are made than it will move in the calibrated magBase direction
                                                                                    # 225 = max speed
                                                                                    # commands [id][0] refers to the input command ie: m0.25, [1:] returns 0.25 the duration the sphereo should move, makes float 
                    time.sleep(0.5)  # Wait for half a second after movement is made 


                elif (commands[id][0][0] == "R"):  # Rotate command, need two inputs ie: R90 0<
                    direction += int(commands[id][0][1:])  # Update the direction, direction = the converted integer of anything after R ie: 90
                                                           # += to keep a record of the sitance turned throughout the program
                                                           # if you wanted print (direction) should = 90

                elif (commands[id][0] == "Cred"):  # Cred sets the color to red, only expecting Cred
                    choosenColor = Color(r = 255, g = 0, b = 0) # ration of red green and blue to = red
                    api.set_main_led(choosenColor) # sets main led = color
                    api.set_front_led(choosenColor) # sets front led = color
                    api.set_back_led(choosenColor) # sets back led = color

                elif (commands[id][0] == "Cgreen"):  # Set color to green
                    choosenColor = Color(r = 0, g = 255, b = 0)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)

                elif (commands[id][0] == "Cblue"):  # Set color to blue
                    choosenColor = Color(r = 0, g = 0, b = 255)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)

                elif (commands[id][0] == "Cblack"):  # Set color to black
                    choosenColor = Color(r = 0, g = 0, b = 0)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)

                elif (commands[id][0] == "Cwhite"):  # Set color to white
                    choosenColor = Color(r = 255, g = 255, b = 255)
                    api.set_main_led(choosenColor)
                    api.set_front_led(choosenColor)
                    api.set_back_led(choosenColor)

                elif (commands[id][0][0] == "d"):  # Delay command, expecting 2 inputs ie: d0.25
                    time.sleep(float(commands[id][0][1:]))  # Wait for specified duration than sleeps the robot for the given time
                                                            # gets duration with the [1:], converts to float as well

                else:  # Handle invalid commands
                    print(commands[id][0] + " in ball {} is an invalid command!".format(id)) # print command is wrong

                # allReady is a 2d list where each inner list (readiness) contains readiness states for a particular Sphero.
                # numIterations: This is an integer that indicates the current iteration or command position.
                commands[id] = commands[id][1:]  # Remove first command, ensures next command will be processed, each command handeled in appeared order
                allReady[id][numIterations] = 1  # Mark this iteration as ready, makes sure all spheros are ready (allReady = 2D List) **
                while True:  # Wait until all toys are ready for the next iteration, infinite loop that keeps checking until all ready 
                    ready = True
                    for readiness in allReady:  # Iterates through each list in the allReady 2D list. Each readiness list corresponds to the readiness statuses for commands of a particular Sphero.
                        if (readiness[numIterations] == 0):  # Accesses the element in the readiness list at the index numIterations. This represents the readiness status of the command at that position.
                                                             # if = 0, the command is not finished and the spheros are not ready, check if command is finished
                            ready = False  # all spheros are not ready for next interations of commands
                            break # breaks loops for readiness in allReady, not the infinite while loop
                    if (ready):  # Exit the loop if all toys are ready, this exits the infinte while loop to start the interation from the first if statement
                        break
                numIterations += 1  # Increment the iteration counter
                time.sleep(1)  # Wait for 1 second before processing the next command, than returns to the Mega while loop


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def commandInputs(toys):  # Initialize command inputs for each toy
    global commands  # Access the global commands list
    global allReady  # Access the global allReady list
    
    commands = []  # Initialize the commands list
    allReady = []  # Initialize the allReady list

    command =  ["Cblue", "m0.25", "R90", "m0.25", "R30", "d2", "m0.5", "M10" "%"]  # Define a sample command sequence, INCLUDING M
    for toy in toys:  # Iterate over each toy
        commands.append(command)  # Assign the command sequence to the current toy
        allReady.append([0] * len(command))  # Initialize readiness status for the current toy

def commandReading(toys):
    pass  # Placeholder function for future implementation

def run_toy_threads(toys):  # Function to start threads for controlling each toy
    id = 0  # Initialize toy ID counter
    threads = []  # List to keep track of threads
    
    global commands  # Access the global commands list
    global allReady  # Access the global allReady list

    commandInputs(toys)  # Initialize commands and readiness status

    for toy in toys:  # Iterate over each toy
        thread = threading.Thread(target=toy_manager, args=[toy, id])  # Create a thread (allows peorgram to run multiple operation concurrently ) for each toy,
                                                                       # toy_manager will be run in the new thread, toy and id are the arguments passed through toy_manager
                                                                       # toy_manager is the big method all the commands are written in
        threads.append(thread)  # Add the thread to the list
        thread.start()  # Start the thread
        id += 1  # Increment the toy ID counter
    
    for thread in threads:  # Wait for all threads to complete
        thread.join()       # join the threads, main program only falls through when all threads are complete 
        
    print("Ending function...")  # Print a message indicating the end of the function

toys = scanner.find_toys()  # Find available Sphero toys

print(toys)  # Print the list of found toys

try: 
    for toy in toys:  # Attempt to calibrate and reset each toy
        with SpheroEduAPI(toy) as api:  # Open a connection to the Sphero toy
            api.calibrate_compass()  # Calibrate the compass
            api.reset_aim()  # Reset the aim
except:  # Handle exceptions
    print("Error!")  # Print an error message
    sys.exit()  # Exit the program

run_toy_threads(toys)  # Start the threads to control the toys
