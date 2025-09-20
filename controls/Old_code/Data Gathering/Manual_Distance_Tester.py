from spherov2 import scanner 
from spherov2.sphero_edu import SpheroEduAPI
import csv

toy = scanner.find_toy(toy_name="SB-CEB2") # can't use normal find toy in conjunction "SB-76B3", "SB-1840", "SB-B11D"
# seems to raise bleak exception errors if it is done that way 

print(toy)

test_seconds = float(input("Number of seconds: "))
speed = int(input("Speed of the ball: "))

with SpheroEduAPI(toy) as api:
    api.roll(0, speed, test_seconds) 

data = [
    [test_seconds, speed, (input("Distance Traveled: "))]
]

with open('distance.csv', 'a', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(data)
