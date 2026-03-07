import subprocess
import sys
import time

# Use the same Python interpreter that's running this script
python_executable = sys.executable

# Start server as a module
server = subprocess.Popen(
    [python_executable, "-m", "controls.Fall_2025_Sphero_Swarm_Server"]
)

# Give server time to bind to the port
time.sleep(10)

# Start client (adjust if your client is also a module)
client = subprocess.Popen(
    [python_executable, "driver.py"]
)

# Wait for client to finish
client.wait()

# Stop the server afterward (optional)
server.terminate()