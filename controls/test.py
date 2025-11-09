import threading
import time

def target_func(num):
    global KILL_FLAG
    for i in range(0, 5, 1):
        print("{}".format(num))
        time.sleep(1)
        if (KILL_FLAG == 1):
            break

global KILL_FLAG
KILL_FLAG = 0

threads = []
for i in range(0, 5, 1):
    thread = threading.Thread(target=target_func, args=[i])
    threads.append(thread)
    thread.start()

# while all threads are not dead
try:
    while (not all([not thread.is_alive() for thread in threads])):
        time.sleep(0.01)
except KeyboardInterrupt:
    KILL_FLAG = 1
    print("Early interupt")

for thread in threads:
    thread.join()