import multiprocessing
import time

def producer(file_path, data_queue):
    with open(file_path, 'a') as file:  # Open the file in append mode
        for i in range(5):
            file.write(f"Message {i}\n")
            data_queue.put(i)  # Put data in the queue for synchronization
            print(f"Producer: Wrote message {i} to file {file_path}")
            time.sleep(1)  # Simulate some processing time

if __name__ == "__main__":
    producer_file_path = 'shared_file.txt'  # Same file for producer and consumer
    data_queue = multiprocessing.Queue()

    producer_process = multiprocessing.Process(target=producer, args=(producer_file_path, data_queue))
    producer_process.start()

    producer_process.join()

    print("Producer process finished")
