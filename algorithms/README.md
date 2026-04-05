# Algorithms Subteam

## Simulation

### Running the Simulation (on VSCode)

* Run the file [`simulation.py`](simulation.py) as a module **from the spheroswarm/ directory** using command:
```bash
python -m algorithms.simulation
```

### If Pygame is not installed

Install pygame:

   ```bash
   python -m pip install pygame
   ```


## Algorithms Folder — File Overview

This section summarizes the purpose, key components, and usage connections of the Python files in `algorithms/`.

### [constants.py](constants.py)

* **Purpose:** Defines shared constants (grid dimensions, sphero counts, colors, spacing, velocities). Set initial sphero positions here.
* **Key Components:** `MARGIN`, `DIRECTIONS`, `N_SPHEROS`, `GRID_WIDTH`, `GRID_HEIGHT`, `SIM_DIST`, `SIM_WIDTH`, `SIM_HEIGHT`, `EPSILON`, `INITIAL_POSITIONS`.
* **Used by:** [`algorithm.py`](algorithm.py), [`simulation.py`](simulation.py), [`test.py`](test.py).

### [sphero.py](sphero.py)

* **Purpose:** Defines the `Sphero` class, representing an agent on the grid.
* **Key Components:**

  * Fields: `id`, `x`, `y`, `true_x`, `true_y`, `target_x`, `target_y`, `direction`, `previous_direction`, `color`, `speed`, `bonding_directions`, `group_id`.
  * Methods: `compute_target_position()`, `update_direction()`, `update_target()`, `update_movement()`, `get_position_change()`, `can_bond()`, `__str__()`.
* **Used by:** [`algorithm.py`](algorithm.py), [`simulation.py`](simulation.py), [`bonded_group.py](bonded_group.py)

### [bonded_group.py](bonded_group.py)

* **Purpose:** Defines the 'BondedGroup' class, representing a group of spheros moving in bonded movement together.
* **Key Components:**

  * Class `BondedGroup` with attributes `group_id`, `spheros`, `size`, `box`, `center`, `valid_moves`.
  * Methods: `find_sphero()`, `update_sphero_membership()`, `find_center()`,`rotate_box()`,`update_center()`,`reset_valid_moves()`,`__str__()`
* **Used by:** [`algorithm.py`](algorithm.py).

### [algorithm.py](algorithm.py)

* **Purpose:** Implements movement and bonding logic for Spheros on the grid.
* **Key Components:**

  * Class `Algorithm` with attributes `grid_width`, `grid_height`, `current_grid`, `next_grid`, `n_spheros`, `bonded_groups`.
    * Methods for Bonding(`bond_all_groups()`, `bond_two_groups()`).
    * Methods for Movement(`move_all_groups()`, `find_group_move()`, `check_translation()`, `check_rotation()`).
    * Other helper methods (`__str__()`, `find_all_spheros()`, `find_sphero()`, `find_group()`, `reset_sphero_positions()`, `purge_grid()`)
  * Collaborates with `Sphero` and `BondedGroup`.

### [simulation.py](simulation.py)

* **Purpose:** Provides visualization and the main loop for rectangular-grid simulation.
* **Key Components:**

  * Rendering: `draw_grid()`, `draw_sphero()`.
  * UI helpers: `draw_pause_button()`.
  * Movement: `moving_sphero_to_target()`, `reached_target()`.
  * Entrypoint: runs a `pygame` loop using an `Algorithm` instance.
* **Used by:** Directly runnable as the rectangular-grid simulation. Also used in spheroswarm/driver.py as a visualization.

### [form_instruction.py](form_instruction.py)

* **Purpose:** To be used in collaboration with perceptions information to course correct sphero positions.
* **Key Components:** 
  * nextVectorDirection() gets adjusted course for a sphero given its target position and its current position in the real world.
  * it is not fully implemented or tested.


### [documentation](documentation/)

* **Purpose:** Historical Pygame simulation prototypes.
* **Key Components:** Each defines `Sphero`, `Swarm`, UI buttons, and `run_simulation()`.
* **Notes:** Contain useful reference implementations for UI and bonding behavior from previous semesters. Also contains our deprecated implementation of the simulation with simulated error, which is still a useful reference.

---

## How Things Connect (Big Picture)

* **Core agent model:** [`Sphero`](sphero.py).
* **Group/bond logic:** [`BondedGroup`](bonded_group.py).
* **Decision/movement logic:** [`Algorithm`](algorithm.py), combining `Sphero` + `BondedGroup`.
* **Visualization & demos:** [`simulation.py`](simulation.py), [`sphero-sim-w-grid.py`](sphero-sim-w-grid.py)
* **Shared constants:** [`constants.py`](constants.py).

---

## IMPORTANT NOTE

x is treated as the height, and y is treated as the width. Where (0,0) is the top left corner of the grid and (HEIGHT - 1, WIDTH - 1) is the bottom right corner. 
