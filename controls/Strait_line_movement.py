import time
import threading
from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI, Color
from spherov2.sphero_edu import EventType

# Scan for Sphero robots
toys = scanner.find_toys()
print("Detected Sphero Toys:", [toy.name for toy in toys])

# Define expected device names
LEADER_NAME = "SB-BD0A"
FOLLOWER_NAME = "SB-CEB2"

leader = next((toy for toy in toys if LEADER_NAME in toy.name), None)
follower = next((toy for toy in toys if FOLLOWER_NAME in toy.name), None)

if not leader or not follower:
    print("Error: Could not find both leader and follower Sphero toys. Ensure they are turned on and nearby.")
    exit()

# IR message handling for follower
def on_ir_message_follower(api, channel):
    if channel == 3:  # Move command
        api.set_speed(31)
        api.set_main_led(Color(156, 255, 206))  # Move color
    elif channel == 4:  # Stop command
        api.set_main_led(Color(251, 0, 255))  # Stop color
        api.stop()

# Collision event handler
def on_collision(api):
    print("Collision detected!")
    api.set_main_led(Color(255, 0, 0))  # Red color for collision
    api.stop()
    time.sleep(1)
    api.set_main_led(Color(141, 255, 72))  # Restore original color

# Freefall event handler
def on_freefall(api):
    print("Freefall detected!")
    api.set_main_led(Color(0, 0, 255))  # Blue color for freefall
    api.stop()
    time.sleep(1)
    api.set_main_led(Color(141, 255, 72))  # Restore original color

# Follower program
def follower_program(sphero):
    with SpheroEduAPI(sphero) as api:
        api.set_main_led(Color(141, 255, 72))  # Start color
        api.register_event(EventType.on_ir_message_received, on_ir_message_follower)
        api.register_event(EventType.on_collision, on_collision)
        api.register_event(EventType.on_freefall, on_freefall)
        
        while True:  # Keep the script alive
            time.sleep(1)

# Leader's waypoint navigation
def waypoint_navigation(leader):
    with SpheroEduAPI(leader) as api:
        api.calibrate_compass()
        api.reset_aim()
        api.set_stabilization(True)
        api.start_ir_broadcast(0, 1)  # Enable IR broadcasting
        
        colors = [Color(255, 125, 241), Color(69, 255, 39), Color(0, 11, 255), Color(255, 0, 16)]
        angles = [0, 90, 180, 270]
        
        for i in range(5):
            for color, angle in zip(colors, angles):
                api.scroll_matrix_text('Purdue ARC', color, 6, wait=True)
                
                api.send_ir_message(3, 64)  # Move command
                time.sleep(0.2)  # Ensure follower receives it
                
                api.roll(angle, 50)
                time.sleep(1)  # Allow movement
                
                api.send_ir_message(4, 64)  # Stop command
                time.sleep(2)  # Pause between movements
        
        api.stop_ir_broadcast()

# Run follower in a separate thread
if __name__ == "__main__":
    follower_thread = threading.Thread(target=follower_program, args=(follower,))
    follower_thread.start()
    
    waypoint_navigation(leader)
    
    follower_thread.join()  # Ensure the follower stops when leader is done.