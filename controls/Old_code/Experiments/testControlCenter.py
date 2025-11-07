import subprocess
import time

if __name__ == "__main__":
    # Start the producer script as a subprocess
    producer_process = subprocess.Popen(["python", "testProducer.py"])

    # Start the consumer script as a subprocess
    consumer_process = subprocess.Popen(["python", "testConsumer.py"])

    # Wait for both subprocesses to finish
    producer_process.wait()
    consumer_process.wait()

    print("Both processes finished")
