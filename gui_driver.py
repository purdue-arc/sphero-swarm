import pickle

from algorithms.constants import Constants
from algorithms.algorithm import Algorithm
from gui_server import send_algorithm_state, get_next_command
import time
import socket
from controls.Instruction import Instruction

def _to_int(value, default=None):
    try:
        return int(value)
    except Exception:
        return default


def _extract_path_nodes(cmd_path, grid_w, grid_h):
    """Return validated list of (x, y) waypoints from GUI payload."""
    if not isinstance(cmd_path, list):
        return []

    nodes = []
    for node in cmd_path:
        if not isinstance(node, dict):
            continue
        x = _to_int(node.get("x"))
        y = _to_int(node.get("y"))
        if x is None or y is None:
            continue
        if 0 <= x < grid_w and 0 <= y < grid_h:
            if not nodes or nodes[-1] != (x, y):
                nodes.append((x, y))
    return nodes


def _set_sphero_target_if_free(algorithm, sphero, target_x, target_y):
    """Override a sphero target when the destination node is free."""
    current_occ = algorithm.nodes[target_x][target_y]
    if current_occ not in (0, sphero.id):
        return False

    old_x, old_y = sphero.target_x, sphero.target_y
    if algorithm.nodes[old_x][old_y] == sphero.id:
        algorithm.nodes[old_x][old_y] = 0
    algorithm.nodes[target_x][target_y] = sphero.id

    sphero.target_x = target_x
    sphero.target_y = target_y
    sphero.direction = 0
    return True


def _remove_sphero_from_bond_group(algorithm, sphero_id):
    """Force a sphero into its own bonding group; recalculation can re-bond it."""
    swarm = algorithm.swarm
    current_group_index = swarm.bonded_group_index[sphero_id - 1]
    current_group = swarm.bonded_groups[current_group_index]

    if sphero_id in current_group:
        current_group.remove(sphero_id)

    new_group_index = len(swarm.bonded_groups)
    swarm.bonded_groups.append([sphero_id])
    swarm.bonded_group_index[sphero_id - 1] = new_group_index


def _process_next_edit_ball_move(algorithm, edit_ball_queue):
    """Process one queued edit-ball move without advancing the whole swarm."""
    if not edit_ball_queue:
        return False

    while edit_ball_queue:
        sphero_id, (nx, ny) = edit_ball_queue[0]
        print(sphero_id, nx, ny)
        sphero = algorithm.find_sphero(sphero_id)

        if sphero is None:
            edit_ball_queue.pop(0)
            continue

        sphero.x = sphero.target_x
        sphero.y = sphero.target_y

        print(sphero.x, sphero.y)

        if (sphero.x, sphero.y) == (nx, ny):
            edit_ball_queue.pop(0)
            continue

        _remove_sphero_from_bond_group(algorithm, sphero_id)
        if _set_sphero_target_if_free(algorithm, sphero, nx, ny):
            # Commit this manual step immediately so the final queued move is not lost while paused.
            sphero.x = sphero.target_x
            sphero.y = sphero.target_y
            edit_ball_queue.pop(0)

        algorithm.update_grid_bonds()
        return True

    algorithm.update_grid_bonds()
    return True


def _send_controls_update(sock, algorithm, constants):
    """Send rotate/roll instruction batches for the current sphero state."""
    rotate_instructions = []
    roll_instructions = []

    for sphero in algorithm.spheros:
        direction_change = sphero.get_direction_change()
        rotate_instruction = Instruction(sphero.id, 2, 45 * direction_change, constants.TURN_DURATION)
        rotate_instructions.append(rotate_instruction)

        speed = constants.SPHERO_SPEED

        # If we are going diagonal, adjust speed by a factor of sqrt(2). thanks pythagoras
        if sphero.direction > 0 and sphero.direction % 2 == 0:
            speed = constants.SPHERO_DIAGONAL_SPEED

        roll_instruction = Instruction(sphero.id, 1, speed, constants.ROLL_DURATION)
        print(str(sphero))
        roll_instructions.append(roll_instruction)

    sock.send(pickle.dumps(rotate_instructions))
    sock.recv(1024)

    sock.send(pickle.dumps(roll_instructions))
    sock.recv(1024)

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
    edit_ball_queue: list[tuple[int, tuple[int, int]]] = []

    s = socket.socket()
    port = 1235

    try:
        while True:
            # ---------------------------------------------------------------
            # process at-most-one command each iteration; newer commands win
            processed_edit_move_this_tick = False
            sent_controls_this_tick = False
            cmd = get_next_command(timeout=0)
            if cmd is not None:
                typ = cmd.get("type")
                # always allow toggling the control flag itself
                if typ == "use_controls":
                    use_controls = bool(cmd.get("value"))
                    print(f"[gui_driver] use_controls set to {use_controls}")
                # allow playback controls (start/stop/pause/resume) regardless of use_controls
                elif typ == "start":
                    if (use_controls):
                        s.connect(('localhost', port))

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
                    edit_ball_queue.clear()
                    start_speed = cmd.get("speed", cmd.get("value"))
                    if start_speed is not None:
                        try:
                            step_delay = max(0, float(start_speed))
                            print(f"[gui_driver] speed set to {step_delay} (from start)")
                        except Exception:
                            pass
                    print("[gui_driver] started")
                elif typ == "reset":
                    running = False
                    constants = Constants()
                    edit_ball_queue.clear()
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
                elif typ == "edit_ball":
                    print("[gui_driver] edit mode enabled")
                elif typ == "done_ball":
                    ball_id = _to_int(cmd.get("ball_id"))
                    if not ball_id:
                        print("[gui_driver] done_ball ignored: missing ball_id")
                    else:
                        path_nodes = _extract_path_nodes(
                            cmd.get("path"),
                            algorithm.grid_width,
                            algorithm.grid_height,
                        )
                        if path_nodes:
                            sphero = algorithm.find_sphero(ball_id)
                            if sphero is None:
                                print(f"[gui_driver] done_ball ignored: unknown id {ball_id}")
                            else:
                                # drop leading duplicate of current target position
                                if path_nodes and path_nodes[0] == (sphero.target_x, sphero.target_y):
                                    path_nodes = path_nodes[1:]
                                edit_ball_queue = [item for item in edit_ball_queue if item[0] != ball_id]
                                for node in path_nodes:
                                    edit_ball_queue.append((ball_id, node))
                                print(f"[gui_driver] queued path for {ball_id}: {path_nodes}")
                                if _process_next_edit_ball_move(algorithm, edit_ball_queue):
                                    if use_controls and running:
                                        _send_controls_update(s, algorithm, constants)
                                        sent_controls_this_tick = True
                                    print("NEW_MOVE")
                                    send_algorithm_state(algorithm)
                                    processed_edit_move_this_tick = True
                        else:
                            edit_ball_queue = [item for item in edit_ball_queue if item[0] != ball_id]
                            print(f"[gui_driver] cleared path for {ball_id}")
                else:
                    print(f"[gui_driver] unknown command: {cmd}")

            if edit_ball_queue and not processed_edit_move_this_tick:
                if _process_next_edit_ball_move(algorithm, edit_ball_queue):
                    if use_controls and running:
                        _send_controls_update(s, algorithm, constants)
                        sent_controls_this_tick = True
                    print("NEW EDIT BALL MOVE")
            elif running and not paused:
                for sphero in algorithm.spheros:
                    sphero.x = sphero.target_x
                    sphero.y = sphero.target_y
                algorithm.update_grid_bonds()
                algorithm.update_grid_move()
                if use_controls and not sent_controls_this_tick:
                    _send_controls_update(s, algorithm, constants)
                    sent_controls_this_tick = True

                print("NEW_MOVE")

            send_algorithm_state(algorithm)

            time.sleep(step_delay)
    except Exception as e:
        print(f"[gui_driver] exception: {e}")
        pass