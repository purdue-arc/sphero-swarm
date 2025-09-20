from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.commands.drive import DriveFlags
import time

# Connect to both Spheros
toys = scanner.find_toys(toy_names=["SB-1840", "SB-E274"])
spheros = [SpheroEduAPI(toy).__enter__() for toy in toys]

# Movement parameters
speed = 100                  # Speed (0-255)
duration = 1.0               # Time to move (seconds)
direction_flag = DriveFlags.FORWARD  # Change to BACKWARD if needed

try:
    print("Starting movement...")
    start_time = time.time()
    
    # Start both Spheros moving
    for sb in spheros:
        sb._SpheroEduAPI__toy.drive_with_heading(speed, 0, direction_flag)  # Heading 0 = forward
    
    # Display distances while moving
    while time.time() - start_time < duration:
        distances = [sb.get_distance() for sb in spheros]
        print(f"Time: {time.time()-start_time:.1f}s | Sphero 1: {distances[0]:.1f} units | Sphero 2: {distances[1]:.1f} units")
        time.sleep(0.1)  # Update rate
    
    # Stop both Spheros
    for sb in spheros:
        sb.stop_roll()
    
    # Final distance report
    final_distances = [sb.get_distance() for sb in spheros]
    print("\nFinal distances:")
    print(f"Sphero 1: {final_distances[0]:.1f} units")
    print(f"Sphero 2: {final_distances[1]:.1f} units")

finally:
    # Cleanup
    for sb in spheros:
        sb.__exit__(None, None, None)
    print("Disconnected from both Spheros")