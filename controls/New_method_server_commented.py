from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import threading
from threading import Lock
import Instruction
import time
import pickle #send instructions over a network
import socket

TIME = 0.5 #Constant for time

def connect_ball(toy, sb_list): # attepts to connect to a sphero 
    sb = 0
    try:
        sb = SpheroEduAPI(toy).__enter__() #establishes the connetion
        sb_list.append(sb) # add it to the list of connected balls 
        print(sb)
    except Exception:
        print("Connection Failure")

def terminate_ball(sb):
    sb.__exit__(None, None, None)

def run_command(instruction, sb): #robot and Intruction which is an object of commands
    global on #Varible to signify the start and end of program, used to shut down when turned off
              #Only tunred on at begining of program 
    print("{}: {}".format(sb._SpheroEduAPI__toy, instruction.type))
    match (instruction.type):
        case 0:
            sb.set_main_led(instruction.color) #set main led, getting data from loaded in insturction through pickel
        case 1:
            sb.roll(sb.get_heading(), instruction.speed, instruction.duration)# gets parameters for roll command from pickel
        case 2:
            sb.spin(instruction.degrees, instruction.duration)#gets parameters for roll command from pickel
        case 3:
            on = False # set to false to know to terminate the program

def control(): #socket server 
    global on
    lock = Lock() #Initialize the lock
    s = socket.socket() #creates the socket
    port = 1234 #port number used to establish a connection
    s.bind(('localhost', port))  
    s.listen(5) #listens for a connection to the socekt
    print("Waiting for connection")
    c, address = s.accept() 
    while (on):
        try:
            instructionList = pickle.loads(c.recv(1024)) #pickel used to serilaze the insturctions from the client 
        except EOFError:
            print("EOFError")
            s.close()#closes the connection
            on = False
        try:
            lock.acquire() #lock this part 
            for instruction in instructionList:
                if (instruction.type == 3): #signifies breaking out of the loop after the command is recieved
                    on = False
                    print("TERMINATION COMMAND RECIEVED")
                if (not (instruction.spheroID < len(command_arr))): #makes sure that you are not acessing a command for a sphero that does not exist
                    print("index out of bounds") 
                else:
                    command_arr[instruction.spheroID].append(instruction) #appends the instruction to the command array at the sheros index
        finally:
            lock.release()

toy_names = ["SB-B5A9", "SB-1840", "SB-76B3", "SB-E274", "SB-BD0A"] #specefied toy names 
toys = []
attempts = 0
while (len(toys) != len(toy_names) and attempts < 5): #ensures that all spheros are found and connected
    toys = scanner.find_toys(toy_names=toy_names)
    attempts += 1
print(toys)
if (len(toys) != len(toy_names) and attempts >= 5): #if not than throw a runtime error 
    raise RuntimeError("Not all balls actually connected")
sb_list = []

global command_arr
command_arr = []
for i in range(0, len(toys), 1): #from 0 to how many toys you have conneted to
    command_arr.append([]) #appends an empty array to the command array to keep track of all the spheros 
global on
on = True

try:
     # Start a separate thread for the control function, running as a daemon
    cmd_thread = threading.Thread(target=control, daemon=True) 
    cmd_thread.start()
    threads = []

    # attempt to quickly connect via multi-threading, may need to sort things out to make sense
    for toy in toys:
        thread = threading.Thread(target=connect_ball, args=[toy, sb_list], daemon=True) 
        threads.append(thread) #appends thread object to the threads array
        thread.start() #starts the threads
    for thread in threads:
        thread.join() # joins, waits for all threads to finish before continuing
    print(sb_list)
    if (len(sb_list) != len(toy_names)): #check list to amke sure the size mathces and all spheros are connected
        raise RuntimeError("Error: Not Actually Connected")

    while (on):
        threads = []
        # Process available commands in the command_arr in a multi-threaded way
        for i in range(0, len(command_arr), 1):
            if (len(command_arr[i]) != 0):
                thread = threading.Thread(target=run_command, args=[command_arr[i].pop(0), sb_list[i]], daemon = True)
                threads.append(thread)
                thread.start()
        for thread in threads:
            thread.join()
        time.sleep(TIME)

finally:
    on = False
    threads = []
    for sb in sb_list:
        thread = threading.Thread(target=terminate_ball, args=[sb], daemon=True)
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    cmd_thread.join()
