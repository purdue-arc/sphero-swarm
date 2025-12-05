# Algorithms Subteam

## Simulation

### Running the Simulation (on VSCode)

* Run the file [`simulation.py`](simulation.py) directly.

### If Pygame is not installed

Install pygame:

   ```bash
   python -m pip install pygame
   ```


## Algorithms Folder — File Overview

This section summarizes the purpose, key components, and usage connections of the Python files in `algorithms/`.

### [constants.py](constants.py)

* **Purpose:** Defines shared constants (grid dimensions, sphero counts, colors, spacing, velocities).
* **Key Components:** `MARGIN`, `DIRECTIONS`, `N_SPHEROS`, `GRID_WIDTH`, `GRID_HEIGHT`, `SIM_DIST`, `SIM_WIDTH`, `SIM_HEIGHT`, `EPSILON`.
* **Used by:** [`algorithm.py`](algorithm.py), [`simulation.py`](simulation.py), [`test.py`](test.py).

### [sphero.py](sphero.py)

* **Purpose:** Defines the `Sphero` class, representing an agent on the grid.
* **Key Components:**

  * Fields: `id`, `x`, `y`, `target_x`, `target_y`, `direction`, `previous_direction`, `color`, `speed`.
  * Methods: `compute_target_position()`, `update_direction()`, `update_target()`, `update_movement()`, `get_position_change()`, `can_bond()`, `__str__()`.
* **Used by:** [`algorithm.py`](algorithm.py), [`sphero-sim-w-grid.py`](sphero-sim-w-grid.py).

### [swarm.py](swarm.py)

* **Purpose:** Tracks bonded groups of Spheros.
* **Key Components:**

  * Class `Swarm` with attributes `bonded_groups`, `bonded_group_index`.
  * Methods: `find_bonding_group()`, `is_bonded()`, `combine()`.
* **Used by:** [`algorithm.py`](algorithm.py).

### [algorithm.py](algorithm.py)

* **Purpose:** Implements movement and bonding logic for Spheros on the grid.
* **Key Components:**

  * Class `Algorithm` with:

    * Grid setup (`nodes`, `spheros`).
    * Methods for initialization (`generate_random_grid()`, `random_initial_position()`).
    * Movement (`is_valid_move()`, `find_valid_move()`, `update_nodes()`, `update_grid_move()`).
    * Bonding (`update_sphero_bonds()`, `update_grid_bonds()`).
  * Collaborates with `Sphero` and `Swarm`.

### [simulation.py](simulation.py)

* **Purpose:** Provides visualization and the main loop for rectangular-grid simulation.
* **Key Components:**

  * Rendering: `draw_grid()`, `draw_sphero()`.
  * UI helpers: `draw_pause_button()`.
  * Movement: `moving_sphero_to_target()`, `reached_target()`.
  * Entrypoint: runs a `pygame` loop using an `Algorithm` instance.
* **Used by:** Directly runnable as the rectangular-grid simulation.

### [documentation](documentation/)

* **Purpose:** Historical Pygame simulation prototypes.
* **Key Components:** Each defines `Sphero`, `Swarm`, UI buttons, and `run_simulation()`.
* **Notes:** Contain useful reference implementations for UI and bonding behavior.

---

## How Things Connect (Big Picture)

* **Core agent model:** [`Sphero`](sphero.py).
* **Group/bond logic:** [`Swarm`](swarm.py).
* **Decision/movement logic:** [`Algorithm`](algorithm.py), combining `Sphero` + `Swarm`.
* **Visualization & demos:** [`simulation.py`](simulation.py), [`sphero-sim-w-grid.py`](sphero-sim-w-grid.py), `documentation/*.py`.
* **Shared constants:** [`constants.py`](constants.py).

---


## Running the Demo

### 1. Update Sphero IDs
- Change the Sphero IDs in the constants (wherever `SB` is defined) to the IDs of the Spheros being used for the demo.

---

### 2. Run the Server
```bash
python3 Fall_2025_Sphero_Swarm_Server.py
```
Wait until the server displays: 
```
waiting for connection from client
```

### Run the Client
- Open a **new terminal**
- Make sure you are in the **root directory**
- Run:
```bash
python3 driver.py


## IMPORTANT NOTE

x is treated as the height, and y is treated as the width. Where (0,0) is the top left corner of the grid and (HEIGHT - 1, WIDTH - 1) is the bottom right corner. 

## TODO
