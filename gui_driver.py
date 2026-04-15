import pickle
import socket
import time

from algorithms.algorithm import Algorithm
from algorithms.constants import Constants
from algorithms.form_instruction import nextVectorDirection
from algorithms.sphero import Sphero
from controls.Instruction import Instruction
import math
from gui_server import get_next_command, send_algorithm_state


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


def _build_algorithm(constants: Constants) -> Algorithm:
    algorithm_spheros = []
    sphero_id = 1
    for (x, y), trait in zip(constants.INITIAL_POSITIONS, constants.INITIAL_TRAITS):
        algorithm_spheros.append(Sphero(sphero_id, x, y, direction=1, trait=trait))
        sphero_id += 1

    return Algorithm(
        grid_width=constants.GRID_WIDTH,
        grid_height=constants.GRID_HEIGHT,
        spheros=algorithm_spheros,
    )


def _set_sphero_position_if_free(algorithm: Algorithm, sphero_id: int, target_x: int, target_y: int) -> bool:
    """Teleport sphero to a GUI-selected node if destination is free."""
    sphero = algorithm.find_sphero(sphero_id)
    if sphero is None:
        return False

    occupant = algorithm.current_grid[target_x][target_y]
    if occupant not in (0, sphero.id):
        return False

    algorithm.current_grid[sphero.x][sphero.y] = 0

    sphero.x = target_x
    sphero.y = target_y
    sphero.target_x = target_x
    sphero.target_y = target_y
    sphero.direction = 0

    algorithm.current_grid[target_x][target_y] = sphero.id
    return True


def _process_next_edit_ball_move(algorithm: Algorithm, edit_ball_queue: list[tuple[int, tuple[int, int]]]) -> bool:
    """Process one queued edit-ball move without advancing the entire swarm."""
    if not edit_ball_queue:
        return False

    sphero_id, (nx, ny) = edit_ball_queue.pop(0)
    moved = _set_sphero_position_if_free(algorithm, sphero_id, nx, ny)
    return moved


def _rebond_from_current_positions(algorithm: Algorithm) -> Algorithm:
    """
    Rebuild bonded groups from current sphero positions using canonical bonding rules.

    This allows edit-ball moves to both split and merge groups correctly.
    """
    spheros = []
    for s in algorithm.find_all_spheros():
        spheros.append(
            Sphero(
                s.id,
                s.x,
                s.y,
                target_x=s.x,
                target_y=s.y,
                previous_direction=s.previous_direction,
                direction=0,
                trait=s.trait,
            )
        )

    spheros.sort(key=lambda s: s.id)
    rebuilt = Algorithm(
        grid_width=algorithm.grid_width,
        grid_height=algorithm.grid_height,
        spheros=spheros,
    )

    # Keep bonding until no more merges occur.
    while True:
        prev_count = len(rebuilt.bonded_groups)
        rebuilt.bond_all_groups()
        if len(rebuilt.bonded_groups) == prev_count:
            break

    return rebuilt


def _send_controls_update(
    sock: socket.socket,
    algorithm: Algorithm,
    constants: Constants,
    use_algorithm_colors: bool,
) -> None:
    """Send color/rotate/roll instruction batches for the current sphero state."""
    color_instructions = []
    rotate_instructions = []
    roll_instructions = []

    custom_palette = constants.COLORS if len(constants.COLORS) > 0 else [constants.WHITE]

    for sphero in algorithm.find_all_spheros():
        if use_algorithm_colors:
            r, g, b = sphero.color[0], sphero.color[1], sphero.color[2]
        else:
            custom_color = custom_palette[(sphero.id - 1) % len(custom_palette)]
            r, g, b = custom_color[0], custom_color[1], custom_color[2]

        color_instructions.append(
            Instruction(sphero.id, 0, r, g, b)
        )

        direction_change = sphero.get_direction_change()
        rotation = False
        if direction_change >= 9:
            rotation = True
            
        delta_angle = nextVectorDirection(sphero)
        rotate_instructions.append(
            Instruction(sphero.id, 2, delta_angle, constants.TURN_DURATION)
        )

        speed = constants.SPHERO_SPEED
        if sphero.direction > 0 and sphero.direction % 2 == 0:
            speed = constants.SPHERO_DIAGONAL_SPEED
        if rotation:
            speed = int(abs(constants.SPHERO_SPEED * math.hypot((sphero.y - sphero.target_y), (sphero.x - sphero.target_x))))

        roll_instructions.append(
            Instruction(sphero.id, 1, speed, constants.ROLL_DURATION)
        )

    sock.send(pickle.dumps(color_instructions))
    sock.recv(1024)

    sock.send(pickle.dumps(rotate_instructions))
    sock.recv(1024)

    sock.send(pickle.dumps(roll_instructions))
    sock.recv(1024)


def _connect_controls(port: int) -> socket.socket:
    sock = socket.socket()
    sock.connect(("localhost", port))
    return sock


if __name__ == "__main__":
    constants = Constants()
    algorithm = _build_algorithm(constants)

    running = False
    paused = False
    use_controls = False
    use_algorithm_colors = True
    controls_sock = None

    step_delay = 4.0
    edit_ball_queue: list[tuple[int, tuple[int, int]]] = []
    port = 1235

    try:
        while True:
            processed_edit_move_this_tick = False
            sent_controls_this_tick = False

            cmd = get_next_command(timeout=0)
            if cmd is not None:
                typ = cmd.get("type")

                if typ == "use_controls":
                    use_controls = bool(cmd.get("value"))
                    print(f"[gui_driver] use_controls set to {use_controls}")
                    if not use_controls and controls_sock is not None:
                        controls_sock.close()
                        controls_sock = None

                elif typ == "use_algorithm_colors":
                    use_algorithm_colors = bool(cmd.get("value"))
                    print(f"[gui_driver] use_algorithm_colors set to {use_algorithm_colors}")

                elif typ == "start":
                    constants = Constants()
                    algorithm = _build_algorithm(constants)
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

                    if use_controls and controls_sock is None:
                        controls_sock = _connect_controls(port)
                    print("[gui_driver] started")

                elif typ == "reset":
                    running = False
                    paused = False
                    constants = Constants()
                    algorithm = _build_algorithm(constants)
                    edit_ball_queue.clear()
                    print("[gui_driver] reset")

                elif typ == "pause" and running:
                    paused = True
                    print("[gui_driver] paused")

                elif typ == "resume" and running:
                    paused = False
                    print("[gui_driver] resumed")

                elif typ == "speed":
                    try:
                        step_delay = max(0, float(cmd.get("value", step_delay)))
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
                        edit_ball_queue = [item for item in edit_ball_queue if item[0] != ball_id]
                        for node in path_nodes:
                            edit_ball_queue.append((ball_id, node))
                        print(f"[gui_driver] queued path for {ball_id}: {path_nodes}")

                else:
                    print(f"[gui_driver] unknown command: {cmd}")

            if edit_ball_queue and not processed_edit_move_this_tick:
                if _process_next_edit_ball_move(algorithm, edit_ball_queue):
                    # Rebuild groups from current positions so bonds reflect true
                    # head/tail rules and can both split and merge.
                    algorithm = _rebond_from_current_positions(algorithm)
                    if running and use_controls and controls_sock is not None:
                        _send_controls_update(
                            controls_sock,
                            algorithm,
                            constants,
                            use_algorithm_colors,
                        )
                        sent_controls_this_tick = True
                    processed_edit_move_this_tick = True
                    print("NEW EDIT BALL MOVE")

            elif running and not paused:
                for sphero in algorithm.find_all_spheros():
                    sphero.x = sphero.target_x
                    sphero.y = sphero.target_y

                algorithm.bond_all_groups()
                algorithm.move_all_groups()

                if use_controls and controls_sock is None:
                    controls_sock = _connect_controls(port)
                if use_controls and controls_sock is not None and not sent_controls_this_tick:
                    _send_controls_update(
                        controls_sock,
                        algorithm,
                        constants,
                        use_algorithm_colors,
                    )
                    sent_controls_this_tick = True

                print("NEW_MOVE")

            send_algorithm_state(algorithm)
            time.sleep(10-step_delay)

    except Exception as error:
        print(f"[gui_driver] exception: {error}")
    finally:
        if controls_sock is not None:
            controls_sock.close()
