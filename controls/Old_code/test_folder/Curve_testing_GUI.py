import tkinter as tk
from tkinter import ttk 
import threading
import time
import math
from spherov2.sphero_edu import SpheroEduAPI
from spherov2 import scanner

current_speed = None
current_heading_increment = None
current_timing_ms = None

# --- Control Flags ---
is_running = False       
sphero_thread = None     
sb_address = None       

def sphero_loop():
    """
    This function runs in a separate thread.
    It connects to the Sphero and runs the main movement loop.
    """
    global is_running
    is_running = True
    print(f"THREAD: Connecting to {sb_address}...")

    try:
        with SpheroEduAPI(sb_address) as api:
            print("THREAD: Connection successful.")
            heading = 0
            
            while is_running:
                # 1. Get current values from the GUI sliders
                speed = current_speed.get()
                increment = current_heading_increment.get()
                
                # 2. Convert timing from ms (slider) to seconds (time.sleep)
                timing_sec = current_timing_ms.get() / 1000.0
                
                api.set_speed(speed)
                api.set_heading(heading)
                heading = (heading + increment) % 360  
                
                # 5. Wait for the specified time
                if timing_sec < 0.001:
                    timing_sec = 0.001  
                time.sleep(timing_sec)
                
    except Exception as e:
        print(f"THREAD ERROR: {e}")
    finally:
        # the flag is reset and we know the thread has stopped.
        is_running = False
        print("THREAD: Loop stopped. Sphero will halt and disconnect.")

def start_sphero():
    global sphero_thread, is_running
    if not is_running:
        print("GUI: Start button pressed. Starting Sphero thread...")
        # Start the sphero_loop function in a separate thread
        sphero_thread = threading.Thread(target=sphero_loop, daemon=True)
        sphero_thread.start()
    else:
        print("GUI: Sphero is already running.")

def stop_sphero():
    global is_running
    if is_running:
        print("GUI: Stop button pressed. Signaling Sphero thread to stop...")
        # This flag tells the 'while is_running:' loop in the thread to exit.
        is_running = False
    else:
        print("GUI: Sphero is not running.")

def on_closing():
    global is_running
    print("GUI: Window closed. Stopping thread and exiting...")
    is_running = False  
    root.destroy()      

if __name__ == "__main__":
    print("Looking for sphero address")
    try:
        sb_address = scanner.find_toy(toy_name="SB-B5A9")
        if sb_address is None:
            print("ERROR: Could not find SB-B11D. Make sure it's on and nearby.")
            exit()
        print(f"Address found: {sb_address}")
    except Exception as e:
        print(f"ERROR finding Sphero: {e}")
        exit()

    # 2. Set up the main GUI window
    root = tk.Tk()
    root.title("Sphero Real-Time Controller")
    root.geometry("350x380")  

    # These variables are linked to the sliders.
    current_speed = tk.IntVar(value=50)
    current_heading_increment = tk.IntVar(value=10)
    current_timing_ms = tk.IntVar(value=20)  # Default 20 ms
    
    # 4. Create GUI Widgets (Labels, Sliders, and Buttons)
    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main_frame, text="Speed (0-255)").pack()
    # Create a frame to hold the slider and its value label
    speed_frame = ttk.Frame(main_frame)
    speed_frame.pack(fill=tk.X, pady=(5, 15))
    speed_slider = ttk.Scale(
        speed_frame, from_=0, to=255, 
        orient=tk.HORIZONTAL, variable=current_speed
    )
    # Slider expands to fill, value label stays fixed on the right
    speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    # Add a label linked to the same variable
    ttk.Label(speed_frame, textvariable=current_speed, width=4).pack(side=tk.RIGHT)


    ttk.Label(main_frame, text="Heading Increment (1-90)").pack()
    # Create a frame to hold the slider and its value label
    increment_frame = ttk.Frame(main_frame)
    increment_frame.pack(fill=tk.X, pady=(5, 15))
    increment_slider = ttk.Scale(
        increment_frame, from_=1, to=90, 
        orient=tk.HORIZONTAL, variable=current_heading_increment
    )
    increment_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    # Add a label linked to the same variable
    ttk.Label(increment_frame, textvariable=current_heading_increment, width=4).pack(side=tk.RIGHT)

    ttk.Label(main_frame, text="Timing Between Updates (1-100 ms)").pack()
    # Create a frame to hold the slider and its value label
    timing_frame = ttk.Frame(main_frame)
    timing_frame.pack(fill=tk.X, pady=(5, 15))
    timing_slider = ttk.Scale(
        timing_frame, from_=1, to=100,  # 1ms to 100ms
        orient=tk.HORIZONTAL, variable=current_timing_ms
    )
    timing_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    # Add a label linked to the same variable
    ttk.Label(timing_frame, textvariable=current_timing_ms, width=4).pack(side=tk.RIGHT)

    
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=20)
    
    start_button = ttk.Button(
        button_frame, text="Start", command=start_sphero
    )
    start_button.pack(side=tk.LEFT, padx=10)
    
    stop_button = ttk.Button(
        button_frame, text="Stop", command=stop_sphero
    )
    stop_button.pack(side=tk.RIGHT, padx=10)

    # 5. Set the close-window behavior
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # 6. Start the GUI event loop
    print("Starting GUI. Press 'Start' to move the robot.")
    # root.mainloop() is a blocking call. It runs the GUI
    # and waits for user interaction (clicks, slider moves, etc.).
    root.mainloop()

    print("Application exited.")