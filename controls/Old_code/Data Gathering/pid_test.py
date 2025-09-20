from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
import time

def getIntegral(data, time, dist):
    a = 0
    for point in data:
        a += (dist - point) * time
    return a

def getDerivative(data, time, dist):
    if len(data) < 2:
        return 0
    return ((dist - data[-1]) - (dist - data[-2])) / (time[-1] - time[-2])

# values for operation
toy_name = scanner.find_toy(toy_name = "SB-76B3")
speed = int(input("Speed of the ball: "))
heading = int(input("Heading: "))
operational_time = float(input("Number of seconds: "))
distance = float(input("Enter distance: "))

# place data gather values below
# starting off with blank data to avoid index issues with getDerivative()
location_data = []
time_data = []
timeStep = 0.1

# PID gains
pGain = 0.5
iGain = 0.5
dGain = 0 # derivative may not be needed

with SpheroEduAPI(toy_name) as bolt:
    bolt.set_speed(speed)
    bolt.set_heading(heading)
    
    start_time = time.time()
    while (start_time + operational_time > time.time()):
        time_data.append(time.time())
        loc = bolt.get_location()
        location_data.append(loc)
        print(loc)
        proportional = pGain * (distance - loc)
        integral = iGain * getIntegral(location_data, timeStep, distance)
        derivative = dGain * getDerivative(location_data, time_data, distance)
        bolt.set_speed(proportional + integral + derivative)
        time.sleep(timeStep)
