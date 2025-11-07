import time
import threading
from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI, Color, EventType

LEADER_NAME = "SB-BD0A"
FOLLOWER_NAME = "SB-CEB2"

toys = scanner.find_toys(toy_names=[LEADER_NAME, FOLLOWER_NAME])

leader = next((toy for toy in toys if toy.name == LEADER_NAME), None)
follower = next((toy for toy in toys if toy.name == FOLLOWER_NAME), None)

if not leader or not follower:
    print("Error: Could not find both leader and follower Sphero toys. Ensure they are turned on and nearby.")
    exit()

current_angle = 0

def on_ir_message_follower(api, channel):
    if channel == 4:
        api.set_main_led(Color(255, 0, 0))
        api.roll(current_angle, 50, 2)
        time.sleep(2)
        api.set_main_led(Color(0, 255, 0))
        api.listen_for_ir_message((4,))

def follower_program(sphero):
    with SpheroEduAPI(sphero) as api:
        api.set_main_led(Color(0, 255, 0))
        api.register_event(EventType.on_ir_message, on_ir_message_follower)
        api.listen_for_ir_message((4,))
        api.start_ir_follow(0,1)
        while True:
            time.sleep(1)

follower_thread = threading.Thread(target=follower_program, args=(follower,))
follower_thread.daemon = True
follower_thread.start()

try:
    with SpheroEduAPI(leader) as api:
        api.set_main_led(Color(255, 0, 255))
        api.start_ir_broadcast(0, 1)
        angles = [0, 90, 180, 270]
        
        for _ in range(1):  
            for angle in angles:
                current_angle = angle
                api.roll(angle, 50, 2)
                time.sleep(2)
                
                api.send_ir_message(4, 64)
                api.listen_for_ir_message((4,))
                time.sleep(3)
finally:
    print("Navigation complete. Disconnecting Sphero robots.")
    with SpheroEduAPI(leader) as api:
        api.set_main_led(Color(0, 0, 0))
    with SpheroEduAPI(follower) as api:
        api.set_main_led(Color(0, 0, 0))