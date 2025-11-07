import multiprocessing
import time

def consumer(file_path, data_queue):
    while True:
        # Check if the queue is empty before getting data
        while not data_queue.empty():
            data = data_queue.get()  # Get data from the queue for synchronization
            print(f"Consumer: Read data from queue (Data: {data})")
        
        # Read from the file
        with open(file_path, 'r') as file:
            line = file.readline().strip()
            if not line:
                break  # Stop consuming at the end of the file
            print(f"Consumer: Read message '{line}' from file {file_path}")
        
        time.sleep(0.5)  # Add a small delay between iterations

if __name__ == "__main__":
    consumer_file_path = 'shared_file.txt'  # Same file for producer and consumer
    data_queue = multiprocessing.Queue()

    consumer_process = multiprocessing.Process(target=consumer, args=(consumer_file_path, data_queue))
    consumer_process.start()

    consumer_process.join()

    print("Consumer process finished")
