# DNA2.py
# Minimal two-sphero version of DNA.py: 1 sine (G1) and 1 cosine (G2)
#
# Corrected to use the *exact* robust connection/disconnection and
# interactive loop structure from the 6-ball DNAHelix file.
# Modified dna_pattern to visually create a double helix structure.
# Amplitude increased by 1.5x.

# PLEASE READ:
#   - Have Bluetooth on this device prior to running code, to avoid getting a WIN error if you are on Windows OS
#   - This file requires the 'name_to_location_dict.csv' to be in the same directory.

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.commands.drive import DriveFlags
import threading
import time
import math

# --- Connection/Disconnection Functions (Copied *exactly* from DNAHelix.py) ---

def generate_dict_map():
    try:
        ret_dict = dict([])
        with open("name_to_location_dict.csv", "r") as file:
            # purposefully purge first line
            line = file.readline()
            while (True):
                line = file.readline()
                if (not line):
                    break
                cleaned_line = line.strip().split(", ")
                ret_dict.update({cleaned_line[0] : int(cleaned_line[1])})
        return ret_dict
    except:
        raise RuntimeError("Dictionary method failed! Exiting code. (Is name_to_location_dict.csv present?)")

# find avaliable toys in an area, and then if not all balls connected
# after a set number of attempts, this raises an error
def find_balls(names, max_attempts):
    for attempts in range(0, max_attempts, 1):
        print("Attempts to find Spheros: " + str(attempts + 1))
        # find the toys and print what is found
        toys = scanner.find_toys(toy_names = names)
        print("Balls found: {}".format(toys))
        if (len(toys) == len(names)):
            print("Found all Sphero balls")
            return toys
        else:
            print("Failed to find all Sphero balls, retrying...")
    # ran out of attempts
    raise RuntimeError("Not all balls found")

# now to sort the addresses
def address_sort(addresses, map_to_location):
    # this will sort from lowest to highest location in the csv,
    # this converts address to string then maps it using dictionary
    addresses.sort(key = lambda address : map_to_location[address.__str__().split()[0]])
    print("Sorted Addresses: {}".format(addresses))

# connect a ball and then return the object created to the list
def connect_ball(toy_address, ret_list, location, max_attempts):
    attempts = 0
    while (attempts < max_attempts):
        try:
            sb = SpheroEduAPI(toy_address).__enter__()
            ret_list[location] = sb
            break
        except KeyboardInterrupt:
            print("Please do not terminate... issues will arise if terminated during connection")
            continue
        except:
            attempts += 1
            print("Trying to connect with: {}, attempt {}".format(toy_address, attempts))
            continue

# currently, only really manages 3 at a time??? so maybe break it up to avoid insanely long waits
# future ideas
def connect_multi_ball(toy_addresses, ret_list, max_attempts):
    # hopefully fast enough that control c'ing in this time should not be humanly reactable
    print("Connecting to Spheros...") 

    # active thread tracker
    threads = []    

    # connecting to sb section
    for index in range(0, len(toy_addresses), 1):
        thread = threading.Thread(target=connect_ball, args=[toy_addresses[index], ret_list, index, max_attempts])
        threads.append(thread)
        thread.start()
    
    while True:
        # resync the system now
        try:
            for thread in threads:
                thread.join(timeout=None)
            break
        except KeyboardInterrupt:
            print("Connection ongoning... please don't interupt.") 
            continue

    # verify function
    print("Balls Connected: {}".format(ret_list))
    # brainstorming: if we start getting future type errors, double check here?
    
# terminate ball to free it for future use
def terminate_ball(sb):
    if (sb != None):
        sb.__exit__(None, None, None)

# terminate balls to allow it to be connected to in the future
def terminate_multi_ball(sb_list):
    # should be fast enough to avoid anything silly
    print("DO NOT TERMINATE - ENDING PROCESSES RUNNING")
    # use multi-threading to speed up close out process
    threads = []
    for sb in sb_list:
        if (type(sb) == SpheroEduAPI):    
            thread = threading.Thread(target=terminate_ball, args=[sb])
            threads.append(thread)
            thread.start()

    while True:
        try:            
            # reconnect the system now, should be safe???
            for thread in threads:
                thread.join(timeout=None)
            break

        except KeyboardInterrupt:
            print("KeyboardInterrupt caught, please do not terminate prematurely")
            continue

# --- End of Copied Functions ---


class DNA2:
    def __init__(self):
        self.sb_list = [] # Use empty list, consistent with original file
        self.running = False
        
    def connect_spheros(self):
        """Connect to 2 Spheros using CSV mapping (logic from DNAHelix)"""
        print("🧬 Connecting to Spheros for DNA2 using CSV mapping...")
        
        try:
            # --- MODIFICATION ---
            # Define the specific Spheros we want for DNA2
            ball_names = ["SB-BD0A", "SB-B5A9"] # These should be configured in your CSV
            print(f"Target Spheros for DNA2: {ball_names}")
            
            # --- EXACTLY as in DNAHelix.py ---
            # Generate dictionary mapping from CSV
            name_to_location_dict = generate_dict_map()
            
            # Find the specific Spheros we need
            toys_addresses = find_balls(ball_names, 5)
            
            # Sort addresses to match CSV ordering
            address_sort(toys_addresses, name_to_location_dict)
            
            # Initialize sb_list with correct length
            self.sb_list = [None] * len(toys_addresses)
            
            # Connect to all balls using multi-threading
            connect_multi_ball(toys_addresses, self.sb_list, 10)
            
            # --- MODIFICATION ---
            # Set colors for DNA2 visualization (replaces set_dna_colors)
            try:
                if len(self.sb_list) >= 2:
                    # Set colors: first blue, second red (based on CSV sort order)
                    self.sb_list[0].set_main_led((0,0,255)) # Blue
                    self.sb_list[1].set_main_led((255,0,0)) # Red
                    print("Colors set: Index 0=Blue, Index 1=Red")
            except Exception as e:
                print(f"Warning: Could not set colors: {e}")
            
            print(f"✅ Successfully connected to {len(self.sb_list)} Spheros!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Spheros: {e}")
            return False
    
    def disconnect_spheros(self):
        """Disconnect all Spheros using server termination logic (EXACTLY as in DNAHelix.py)"""
        print("Disconnecting Spheros...")
        terminate_multi_ball(self.sb_list)
        self.sb_list.clear()
        print("All Spheros disconnected.")
    
    def dna_pattern(self):
        """
        DNA2 Pattern: Two robots, both sine wave, creating a double helix look.
        Robot 0 (Blue) will be the first strand, Robot 1 (Red) the second.
        The second strand will be offset slightly in X to prevent direct overlap and
        create the visual separation of the double helix.
        """
        
        if len(self.sb_list) < 2:
            print("Error: Need at least 2 Spheros for DNA2")
            return

        print("🧬 Starting DNA2 Double Helix Pattern (2-ball sine wave)...")
        self.running = True

        # --- MODIFICATION: Amplitude increased by 1.5x ---
        amplitude = 0.12      # meters (how wide the helix is) (0.08 * 1.5)
        # --- End MODIFICATION ---
        
        wavelength = 1.5     # meters (how long one full twist of the helix is)
        speed_units = 85      # Sphero speed units (0-255)
        dt = 0.05             # control loop dt (s)
        meters_per_speed = 0.2 / 60.0
        v_mps = max(0.01, speed_units * meters_per_speed)

        # x_strand_spacing: This is the critical change to give the visual separation
        # A small offset in X direction between the two strands
        x_strand_spacing = wavelength / 8.0 # Example: 1/8th of a wavelength

        # y_bases: Vertical offset for each robot to create vertical separation
        y_bases = [0.10, -0.10] 

        # phases: Half a wavelength difference for the two strands (180 degrees)
        # Robot 0: starts at 0 phase (peak)
        # Robot 1: starts at pi phase (trough)
        phases = [0.0, math.pi]

        # x_starts: Robot 0 starts at 0, Robot 1 starts offset by x_strand_spacing
        x_starts = [0.0, x_strand_spacing]

        # Staggered start is already included to prevent collision:
        start_delays = [0.0, 0.5] # Robot 0 starts immediately, Robot 1 starts 0.5s later

        t0 = time.time()
        started = [False] * len(self.sb_list)

        try:
            while self.running:
                t = time.time() - t0
                
                # Use enumerate(self.sb_list) to iterate through connected robots
                for idx, sb in enumerate(self.sb_list):
                    if sb is None:
                        continue
                    
                    # Stop loop if we are beyond the 2 balls needed for this pattern
                    if idx >= 2:
                        break

                    if not started[idx]:
                        if t < start_delays[idx]:
                            continue
                        else:
                            started[idx] = True
                            
                    # Calculate 'x' based on its initial offset and travel speed
                    x = x_starts[idx] + v_mps * (t - start_delays[idx])
                    
                    # Both robots will follow a sine wave for the helix
                    y = y_bases[idx] + amplitude * math.sin(2 * math.pi * x / wavelength + phases[idx])
                    dy_dx = amplitude * (2 * math.pi / wavelength) * math.cos(2 * math.pi * x / wavelength + phases[idx])
                    
                    try:
                        heading_rad = math.atan2(dy_dx, 1.0) # 1.0 for forward x movement
                        heading_deg = (math.degrees(heading_rad) + 360) % 360
                        sb.set_heading(int(heading_deg))
                        sb.set_speed(speed_units)
                    except Exception:
                        pass
                        
                time.sleep(dt)

        except KeyboardInterrupt:
            print("\nStopping DNA2 pattern (from thread, Ctrl+C detected)...")
            self.stop_pattern()
    
    def stop_pattern(self):
        """Stop the DNA pattern (EXACTLY as in DNAHelix.py)"""
        self.running = False
        for sb in self.sb_list:
            if sb is not None:
                try:
                    sb.set_speed(0)
                except:
                    pass
        print("DNA2 pattern stopped.")
    
    def run_interactive(self):
        """Run interactive DNA2 control (EXACTLY as in DNAHelix.py)"""
        if not self.connect_spheros():
            return
        
        print("\n🧬 DNA2 Controls:")
        print("Commands:")
        print("  start  - Start DNA2 pattern")
        print("  stop   - Stop current pattern")
        print("  quit   - Exit program")
        
        # --- This try/finally block is CRITICAL ---
        # It guarantees disconnect_spheros() runs on exit
        try:
            while True:
                command = input("\nDNA2> ").strip().lower()
                
                if command == "start":
                    if not self.running:
                        print("Starting DNA2 pattern...")
                        t = threading.Thread(target=self.dna_pattern)
                        t.daemon = True # Allow program to exit even if thread is running
                        t.start()
                    else:
                        print("DNA2 pattern is already running!")
                
                elif command == "stop":
                    if self.running:
                        self.stop_pattern()
                    else:
                        print("Pattern is not running.")
                
                elif command == "quit":
                    self.stop_pattern()
                    break # Exit the while loop
                
                else:
                    print("Unknown command. Use: start, stop, quit")
                    
        except KeyboardInterrupt:
            # This is triggered if user hits Ctrl+C from the input prompt
            print("\nExiting due to Ctrl+C...")
            self.running = False # Ensure pattern stops if running
        finally:
            # --- THIS IS THE GUARANTEED DISCONNECT ---
            print("Shutting down and disconnecting Spheros...")
            self.stop_pattern() # Stop any running motion, ensuring balls stop
            self.disconnect_spheros() # Properly disconnect all balls

def main():
    """Main function to run DNA2"""
    print("🧬 DNA2 Sphero Pattern (Double Helix)")
    print("=" * 30)
    
    dna = DNA2()
    dna.run_interactive()

if __name__ == "__main__":
    main()