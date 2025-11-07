# Sphero Swarm Server - Quick Start Guide

A simple Python script to connect to multiple Sphero robots and control them.

## Setup

1. **Install Python package**:
   ```bash
   pip install spherov2
   ```

2. **Enable Bluetooth** on your computer before running

3. **Power on your Sphero robots** and make sure they're in pairing mode

## Robot Configuration

The script is currently set up for these 4 robots:
- SB-CEB2
- SB-B11D  
- SB-76B3
- SB-B5A9

**To use your own robots**: Edit line 145 in `2025_Fall_Sphero_Swarm_Server.py`:
```python
ball_names = ["YOUR_ROBOT_NAME_1", "YOUR_ROBOT_NAME_2", "YOUR_ROBOT_NAME_3", "YOUR_ROBOT_NAME_4"]
```

## How to Run

1. Navigate to the controls folder:
   ```bash
   cd controls
   ```

2. Run the script:
   ```bash
   python 2025_Fall_Sphero_Swarm_Server.py
   ```

3. Wait for connection messages. The script will:
   - Find your robots
   - Connect to them
   - Then immediately disconnect them

## What It Does

- **Connects** to all specified Sphero robots simultaneously
- **Sorts** them by their ID numbers
- **Disconnects** them cleanly when done

## Using Robot Commands

The script includes a `run_command()` function that can control individual robots:

```python
# Change LED color
instruction = Instruction(robot_id, 0, Color.red)
run_command(sb_list[robot_id], instruction)

# Make robot roll forward
instruction = Instruction(robot_id, 1, speed, duration)
run_command(sb_list[robot_id], instruction)

# Make robot turn
instruction = Instruction(robot_id, 2, degrees, duration)
run_command(sb_list[robot_id], instruction)
```

## Troubleshooting

- **"Not all balls actually connected"**: Make sure all robots are powered on and Bluetooth is enabled
- **Connection fails**: Try restarting Bluetooth or power cycling the robots
- **Don't interrupt** the script while it's connecting/disconnecting

## Files Needed

- `2025_Fall_Sphero_Swarm_Server.py` - Main script
- `Instruction.py` - Command definitions  
- `name_to_location_dict.csv` - Robot name to ID mapping
