import subprocess
import time

if __name__ == "__main__":
    # Start the producer script as a subprocess
    producer_process = subprocess.Popen(["python", "producer_script.py"])

    # Start the consumer script as a subprocess
    consumer_process = subprocess.Popen(["python", "consumer_script.py"])

    # Wait for both subprocesses to finish
    producer_process.wait()
    consumer_process.wait()

    print("Both processes finished")