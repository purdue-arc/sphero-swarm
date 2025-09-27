### Algorithms Subteam

## Simulation

# On VSCode 

Simply run file ```sphero-sim-w-grid.py```

# If Pygame is not installed

You may want to create a virtual environment:

``` python3 -m venv env ```

and activate it with 

``` source env/bin/activate ```

Then pip install python using 

```./env/bin/pip install pygame```

Finally, run the file in the virtual environment

```./env/bin/python sphero-sim-w-grid.py```

## Driver

```sphero_driver.py``` is the program used to control the actual spheros.
TODO: Documentation needed for using the driver 


### Algorithms folder — file overview

This section summarizes the purpose, key components, and connections between the Python files in the `algorithms` folder.

- [constants.py](constants.py)
  - Purpose: shared constants for simulations (grid size, spacing, sphero counts, velocities).
  - Key components: `MARGIN`, `DIRECTIONS`, `N_SPHEROS`, `NODES_WIDTH`, `NODES_HEIGHT`, `NODES_DISTANCE`, `WIDTH`, `HEIGHT`, `VELOCITY`.
  - Used by: [`Algorithm`](algorithm.py), [`simulation.py`](simulation.py), [`test.py`](test.py).

- [sphero.py](sphero.py)
  - Purpose: defines the Sphero data object used by algorithms that simulate grid movement and bonding.
  - Key components: class [`Sphero`](sphero.py) with fields `id`, `x`, `y`, `previous_direction`, `direction`; methods `update_direction()`, `get_direction_change()`, `can_bond()`, `__str__()`.
  - Notes: `can_bond` intends to check coordinate adjacency;
  - Used by: [`Algorithm`](algorithm.py), `sphero-sim-w-grid.py` variants in `documentation/` and `sphero-sim-w-grid.py`.

- [swarm.py](swarm.py)
  - Purpose: union-find-like structure tracking bonded groups.
  - Key components: class [`Swarm`](swarm.py) storing `bonded_groups` (list of groups) and `bonded_group_index` (mapping id → group index); methods `is_bonded()` and `combine()`.
  - Used by: [`Algorithm`](algorithm.py) to decide valid moves and merges.

- [algorithm.py](algorithm.py)
  - Purpose: core grid-based movement and bonding logic (Algorithm class for controlling Sphero agents on node grid).
  - Key components:
    - class [`Algorithm`](algorithm.py) with:
      - `position_change` map (direction → delta).
      - initialization logic that creates `nodes` grid and a `spheros` list.
      - methods: `generate_random_grid()`, `random_initial_position()`, `find_sphero()`, `compute_target_position()`, `is_valid_move()`, `find_valid_move()`, `find_bonded_group_move()`, `update_nodes()`, `update_bonded_group_move()`, `update_grid_move()`, `check_bonding()`.
    - Collaborates with [`Swarm`](swarm.py) and [`Sphero`](sphero.py).
  - Notes / issues:


- [simulation.py](simulation.py)
  - Purpose: small utilities for rendering grid and UI elements, plus a script entrypoint that constructs an `Algorithm` instance.
  - Key components:
    - color constants (duplicated here; could use [`constants.py`](constants.py) instead).
    - `draw_grid(surface)` — renders a rectangular grid using values from [`constants`](constants.py) (`WIDTH`, `HEIGHT`, `NODES_DISTANCE`, `DISTANCE` reference — note: `DISTANCE` is not defined in `constants.py`; check usage).
    - UI helpers: `print_bonds()`, `draw_pause_button()`, `draw_rotate_button()`.
    - Main demo code that creates `Algorithm(...)` (constructed from [`algorithm.py`](algorithm.py)).
  - Used by: can be run as a simple visual demo; references [`Algorithm`](algorithm.py).

- [sphero-sim-w-grid.py](sphero-sim-w-grid.py)
  - Purpose: an independent Pygame simulation that draws a triangular grid and simulates sphero bonding/rotation behavior.
  - Key components:
    - grid drawing: `draw_triangular_grid(surface, triangle_size, color)`.
    - button helpers: `draw_pause_button()`, `draw_rotate_button()` with event rectangles returned for interaction.
    - Sphero simulation loop: creates Sphero-like objects, `bonds` groups, movement update/target logic, bonding checks, and UI controls.
  - This file is the primary runnable demo referenced by the top-level algorithms README ("Simply run file `sphero-sim-w-grid.py`").

- [test.py](test.py)
  - Purpose: minimal Pygame test harness that creates a display and calls `draw_grid`.
  - Key components:
    - imports `pygame` and `constants`.
    - calls `draw_grid(screen)` (expects `draw_grid` implementation in `simulation.py` or similar).
  - Notes: `draw_grid` is implemented in [`simulation.py`](simulation.py) — running `test.py` as-is will need that function to be imported or accessible.

- [documentation/*.py](documentation/Sphero Swarm Simulation*.py)
  - Purpose: multiple iterations of simulation prototypes (Sphero Swarm Simulation, Simulation2..7).
  - Key components: each file is a Pygame prototype that defines `Sphero` and `SpheroSwarm` classes, UI `Button` helpers, and a `run_simulation()` entrypoint. Many of them contain similar methods: `update_position()`, `update_velocity()`, `draw()`, `display_raw_data()`.
  - Use: useful references for features like pause/resume, color-change buttons, raw-data display and polymerization behavior.

How things connect (big picture)
- The shared constants in [`constants.py`](constants.py) provide the grid and simulation sizing. The visual rendering functions in [`simulation.py`](simulation.py) use those constants to draw the rectangular grid.
- The core agent model is [`Sphero`](sphero.py). The group/bond logic is implemented by [`Swarm`](swarm.py).
- The decision and movement logic is in [`Algorithm`](algorithm.py) which uses `Sphero` and `Swarm` to compute valid moves and update the `nodes` occupancy grid.
- `sphero-sim-w-grid.py` and the scripts in `documentation/` are runnable demos that implement Pygame loops, use local Sphero-like objects and bonding logic (some replicate behavior from [`Algorithm`](algorithm.py) but keep their own Sphero class definitions).
- `test.py` is a minimal harness to invoke the grid drawing.

Quick pointers to run and improve
- To run the triangular-grid demo: run [sphero-sim-w-grid.py](sphero-sim-w-grid.py).
- To run the rectangular-grid Algorithm demo: run [simulation.py](simulation.py) — it constructs an [`Algorithm`](algorithm.py) instance.
- Consider consolidating duplicated constants (colors, sizes) — move shared colors into [`constants.py`](constants.py).
- Fixes to check:
  - Replace `math.abs` in [`Sphero.can_bond`](sphero.py) with `abs()` or `math.fabs()`.
  - Use a safe 2D list creation in [`Algorithm.__init__`](algorithm.py): `self.nodes = [[0 for _ in range(node_width)] for _ in range(node_height)]` to avoid aliasing rows.
  - Ensure imports work based on how you run scripts (script vs package): some files import using package-style paths (`from algorithms.swarm import Swarm`) which may need to be adjusted when running a file directly.

Relevant files and symbols (quick links)
- [`constants`](constants.py)
- [`Sphero`](sphero.py)
- [`Swarm`](swarm.py)
- [`Algorithm`](algorithm.py)
- [`draw_grid`](simulation.py)
- [sphero-sim-w-grid.py](sphero-sim-w-grid.py)
- [simulation.py](simulation.py)
- [test.py](test.py)
