import subprocess

if __name__ == "__main__":
    # Start the producer script as a subprocess
    process_1 = subprocess.Popen(["python", "arbitrary_file1_test.py"])

    # Start the consumer script as a subprocess
    process_2 = subprocess.Popen(["python", "arbitrary_file2_test.py"])

    # Wait for both subprocesses to finish
    process_1.wait()
    process_2.wait()

    print("Both processes finished")