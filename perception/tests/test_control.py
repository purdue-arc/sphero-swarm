from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.commands.drive import DriveFlags
import time

print("Welcome to controls mimic!")
address = "SB-E274"

# Find the toy
toy = scanner.find_toy(toy_name=address)
if not toy:
    print("Toy not found!")
    exit()

# Connect to the toy
with SpheroEduAPI(toy) as sb:
    print("Connected to Sphero!")

    command = input("Enter command: ")

    while command != "exit":
        if command.startswith("move"):
            try:
                _, speed, duration = command.split()
                speed = int(speed)
                duration = float(duration)
                sb._SpheroEduAPI__toy.drive_with_heading(abs(speed), sb.get_heading(), DriveFlags.FORWARD)

                time.sleep(duration)
                sb.stop_roll()
            except ValueError:
                print("Invalid move command. Use: move <speed> <duration>")

        elif command.startswith("turn"):
            try:
                _, degree = command.split()
                degree = int(degree)

                time_pre_rev = 0.45
                abs_angle = abs(degree)
                duration = max(0.5, time_pre_rev * abs_angle / 360)  # fallback minimum duration

                start = time.time()
                angle_gone = 0

                while angle_gone < abs_angle:
                    elapsed = time.time() - start
                    delta = round(min(elapsed / duration, 1.0) * abs_angle) - angle_gone
                    if delta != 0:
                        sb.set_heading(sb.get_heading() + delta if degree > 0 else sb.get_heading() - delta)
                        angle_gone += delta
            except ValueError:
                print("Invalid turn command. Use: turn <degrees>")


        else:
            print("Unknown command")

        command = input("Enter command: ")

print("Goodbye!")
