from algorithms.constants import Constants
from algorithms.algorithm import Algorithm
from gui_server import send_algorithm_state, get_next_command
import time

if __name__ == "__main__":
    constants = Constants()
    print(constants.INITIAL_POSITIONS, constants.SPHERO_TAGS, constants.N_SPHEROS)
    # start with an algorithm ready but not running until a "start" command
    algorithm = Algorithm(
        constants.GRID_WIDTH,
        constants.GRID_HEIGHT,
        constants.N_SPHEROS,
        constants.COLORS,
        constants.INITIAL_POSITIONS,
    )

    running = False          # controlled by start/stop commands
    paused = False
    use_controls = False     # when False we ignore all commands except enabling controls
    step_delay = 4.0         # base sleep time, adjustable by GUI slider

    try:
        while True:
            # ---------------------------------------------------------------
            # process at-most-one command each iteration; newer commands win
            cmd = get_next_command(timeout=0)
            if cmd is not None:
                typ = cmd.get("type")
                # always allow toggling the control flag itself
                if typ == "use_controls":
                    use_controls = bool(cmd.get("value"))
                    print(f"[gui_driver] use_controls set to {use_controls}")
                # allow playback controls (start/stop/pause/resume) regardless of use_controls
                elif typ == "start":
                    # restart the algorithm from scratch
                    constants = Constants()
                    algorithm = Algorithm(
                        constants.GRID_WIDTH,
                        constants.GRID_HEIGHT,
                        constants.N_SPHEROS,
                        constants.COLORS,
                        constants.INITIAL_POSITIONS,
                    )
                    running = True
                    paused = False
                    print("[gui_driver] started")
                elif typ == "reset":
                    running = False
                    constants = Constants()
                    print("[gui_driver] stopping")
                elif typ == "pause" and running:
                    paused = True
                    print("[gui_driver] paused")
                elif typ == "resume" and running:
                    paused = False
                    print("[gui_driver] resumed")
                elif typ == "speed":
                    try:
                        val = float(cmd.get("value", step_delay))
                        step_delay = max(0, val)
                        print(f"[gui_driver] speed set to {step_delay}")
                    except Exception:
                        pass
                else:
                    print(f"[gui_driver] unknown command: {cmd}")

            if running and not paused:
                for sphero in algorithm.spheros:
                    sphero.x = sphero.target_x
                    sphero.y = sphero.target_y
                algorithm.update_grid_bonds()
                algorithm.update_grid_move()

                send_algorithm_state(algorithm)
                print("NEW_MOVE")
            else:
                # even if we're not stepping forward, still send the current
                # state so clients don't time out waiting for an update.
                send_algorithm_state(algorithm)

            time.sleep(step_delay)
    except Exception as e:
        print(f"[gui_driver] exception: {e}")
        pass