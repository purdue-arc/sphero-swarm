from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
import threading

def control_toy(toy):
    with SpheroEduAPI(toy) as api:
        api.spin(360, 1)

toys = scanner.find_toys()

# Creating and starting a new thread for each toy
threads = []
for toy in toys:
    thread = threading.Thread(target=control_toy, args=(toy,))
    threads.append(thread)
    thread.start()

# Wait for all threads to complete
for thread in threads:
    thread.join()
