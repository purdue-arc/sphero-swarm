import math
import socket
import time
import uuid
import zmq

from algorithms.algorithm import Algorithm
from algorithms.constants import Constants
from algorithms.sphero import Sphero
from controls.Instruction import Instruction
from controls.protocol import send_batch
from gui_server import get_next_command, send_algorithm_state

ROLL_STRAIGHT_INCH = 12.67

def _perception_request(message):
    """Short-lived socket keeps a missing perception process from blocking rolls."""
    sock = zmq.Context.instance().socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.setsockopt(zmq.RCVTIMEO, 1000)
    sock.setsockopt(zmq.SNDTIMEO, 1000)
    try:
        sock.connect("tcp://127.0.0.1:5555")
        if isinstance(message, str):
            sock.send_string(message)
        else:
            sock.send_json(message)
        return sock.recv_json()
    except zmq.ZMQError:
        return None
    finally:
        sock.close()

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
    # Reuse the robots: rebuilding bonds must not erase measurements or heading.
    spheros = sorted(algorithm.find_all_spheros(), key=lambda s: s.id)
    for sphero in spheros:
        sphero.direction = 0
        sphero.group_id = sphero.id
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


def _distance_based_roll(algorithm: Algorithm, sphero: Sphero, constants: Constants):
    """Use calibrated speed and vary duration to cover measured target distance."""
    if not algorithm._has_fresh_measurement(sphero):
        return None
    distance_grid = math.hypot(sphero.target_x - sphero.true_x, sphero.target_y - sphero.true_y)
    if distance_grid <= constants.TARGET_TOLERANCE:
        return None
    distance = ROLL_STRAIGHT_INCH * distance_grid
    return constants.SPHERO_SPEED, distance, max(0.0, algorithm.get_roll_duration(distance))


def _speed_based_roll(algorithm: Algorithm, sphero: Sphero, constants: Constants):
    """Keep the error-correction strategy: vary speed with a fixed roll duration."""
    speed = algorithm.calculate_speed(sphero)
    if speed <= 0:
        return None
    distance = ROLL_STRAIGHT_INCH * math.hypot(
        sphero.target_x - sphero.true_x, sphero.target_y - sphero.true_y
    )
    return speed, distance, constants.ROLL_DURATION


def _send_controls_update(
    sock: socket.socket,
    algorithm: Algorithm,
    constants: Constants,
    use_algorithm_colors: bool,
    roll_strategy=_distance_based_roll,
) -> str:
    """Send color/rotate/roll instruction batches for the current sphero state."""
    color_instructions = []
    rotate_instructions = []
    roll_instructions = []
    targets = []
    trial_id = uuid.uuid4().hex

    if any(not s.heading_valid for s in algorithm.find_all_spheros()):
        print("[gui_driver] Heading uncertain after a controls failure; reset and recalibrate")
        return "failed"

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

        roll = roll_strategy(algorithm, sphero, constants)
        if roll is None:
            continue
        speed, distance, duration = roll
        # Recompute on retries and edited paths as well as algorithm moves.
        sphero.delta_angle = algorithm.calculate_angle_change(sphero)

        rotate_instructions.append(
            Instruction(sphero.id, 2, sphero.delta_angle, constants.TURN_DURATION)
        )

        roll_instructions.append(
            Instruction(sphero.id, 1, speed, duration)
        )
        targets.append({"trial_id": trial_id, "algorithm_id": sphero.id,
                        "id": sphero.id, "x": sphero.target_x, "y": sphero.target_y,
                        "speed": speed, "distance": distance,
                        "duration": duration, "inches_per_step": ROLL_STRAIGHT_INCH})

        algorithm.log(f"sphero: {sphero.id}")
        error_x, error_y = sphero.get_error()
        algorithm.log(
            f"x-error: {ROLL_STRAIGHT_INCH * error_x}\n"
            f"y-error: {ROLL_STRAIGHT_INCH * error_y}\n"
            f"delta angle: {sphero.delta_angle}\ndistance: {distance} inches\n"
            f"duration: {duration} seconds",
            indent=1,
        )

    send_batch(sock, color_instructions)
    if not targets:
        return "complete"
    evaluation = _perception_request({"action": "roll_targets", "targets": targets})
    evaluating = bool(evaluation and evaluation.get("ok"))
    if not evaluating:
        print("[gui_driver] Movement withheld: endpoint evaluation unavailable")
        return "failed"
    turn_outcomes = send_batch(sock, rotate_instructions)
    for instruction in rotate_instructions:
        sphero = algorithm.find_sphero(instruction.spheroID)
        if turn_outcomes.get(str(instruction.spheroID)) == "complete":
            sphero.heading_angle = (sphero.heading_angle + instruction.degrees) % 360
        else:
            # A failed turn can have partially executed. Do not retry it using
            # an estimate of the old direction.
            sphero.heading_valid = False
    valid_rolls = [instruction for instruction in roll_instructions
                   if turn_outcomes.get(str(instruction.spheroID)) == "complete"]
    for instruction in valid_rolls:
        sphero = algorithm.find_sphero(instruction.spheroID)
        sphero.prev_true_x, sphero.prev_true_y = sphero.true_x, sphero.true_y
    outcomes = send_batch(sock, valid_rolls) if valid_rolls else {}
    for instruction in roll_instructions:
        if turn_outcomes.get(str(instruction.spheroID)) != "complete":
            outcomes[str(instruction.spheroID)] = "turn_failed"
    if evaluating:
        _perception_request({"action": "roll_complete", "trial_id": trial_id, "outcomes": outcomes})
        if any(outcomes.get(str(target["algorithm_id"])) != "complete" for target in targets):
            return "failed"
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            result = _perception_request({"action": "roll_results", "trial_id": trial_id})
            if result and result.get("finished"):
                print(f"[gui_driver] Roll evaluation: {result['trials']}")
                trials = result["trials"]
                if ({t["algorithm_id"] for t in trials} != {t["algorithm_id"] for t in targets}
                        or any(t["status"] != "settled" for t in trials)):
                    return "failed"
                return "complete" if all(t.get("passed") is True for t in trials) else "off_target"
            if result is None:
                print("[gui_driver] Perception disconnected during roll evaluation")
                break
            time.sleep(0.1)
        else:
            print("[gui_driver] Roll evaluation timed out; inspect perception tracking")
    return "failed"


def _refresh_positions(algorithm):
    data = _perception_request("coords")
    if not isinstance(data, dict) or not isinstance(data.get("spheros"), list):
        return False
    algorithm.set_true_positions(data)
    seen = {entry.get("id", entry.get("ID")) for entry in data["spheros"]}
    return all(s.id in seen and algorithm._has_fresh_measurement(s)
               for s in algorithm.find_all_spheros())


def _targets_reached(algorithm, constants):
    return all(
        algorithm._has_fresh_measurement(s)
        and math.hypot(s.target_x - s.true_x, s.target_y - s.true_y) <= constants.TARGET_TOLERANCE
        for s in algorithm.find_all_spheros()
    )


def _drive_to_targets(sock, algorithm, constants, use_algorithm_colors, max_attempts=3):
    """Correct the same targets; a failed batch never commits simulated positions."""
    for _ in range(max_attempts):
        if not _refresh_positions(algorithm):
            return False
        if _targets_reached(algorithm, constants):
            return True
        try:
            status = _send_controls_update(sock, algorithm, constants, use_algorithm_colors)
        except (OSError, EOFError) as error:
            print(f"[gui_driver] Controls connection failed: {error}")
            for sphero in algorithm.find_all_spheros():
                sphero.heading_valid = False
            return False
        if status == "failed":
            return False
        # Evaluation waits for a settled endpoint. Refresh before using it to
        # confirm arrival or choose the direction of the next corrective roll.
        if not _refresh_positions(algorithm):
            return False
        if _targets_reached(algorithm, constants):
            return True
    return False


def _restore_current_grid(algorithm):
    algorithm.current_grid = [[0 for _ in range(algorithm.grid_height)]
                              for _ in range(algorithm.grid_width)]
    for sphero in algorithm.find_all_spheros():
        algorithm.current_grid[sphero.x][sphero.y] = sphero.id


def _commit_targets(algorithm):
    for sphero in algorithm.find_all_spheros():
        sphero.x, sphero.y = sphero.target_x, sphero.target_y
    _restore_current_grid(algorithm)


def _set_hardware_edit_target(algorithm, sphero_id, x, y):
    sphero = algorithm.find_sphero(sphero_id)
    if (sphero is None or not 0 <= x < algorithm.grid_width or not 0 <= y < algorithm.grid_height
            or algorithm.current_grid[x][y] not in (0, sphero_id)):
        return False
    sphero.target_x, sphero.target_y = x, y
    return True


def _connect_controls(port: int) -> socket.socket:
    sock = socket.socket()
    sock.connect(("localhost", port))
    sock.recv(1024)  # Controls sends the configured Sphero IDs before instruction acknowledgements.
    return sock


def main_server():
    constants = Constants()
    algorithm = _build_algorithm(constants)
    pending_hardware_move = False
    pending_edit_move = False

    running = False
    paused = False
    use_controls = False
    use_algorithm_colors = True
    controls_sock = None

    step_seconds = 4.0
    next_step_at = 4.0
    edit_ball_queue: list[tuple[int, tuple[int, int]]] = []
    port = 1235

    try:
        while True:
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
                    pending_hardware_move = False
                    pending_edit_move = False
                    next_step_at = step_seconds

                    requested_step_seconds = cmd.get("step_seconds")
                    if requested_step_seconds is not None:
                        try:
                            step_seconds = max(0.1, float(requested_step_seconds))
                            print(f"[gui_driver] step seconds set to {step_seconds} (from start)")
                        except Exception:
                            pass

                    if use_controls and controls_sock is None:
                        controls_sock = _connect_controls(port)
                    print("[gui_driver] started")

                elif typ == "reset":
                    running = False
                    paused = False
                    if controls_sock is not None:
                        controls_sock.close()
                        controls_sock = None
                    constants = Constants()
                    algorithm = _build_algorithm(constants)
                    edit_ball_queue.clear()
                    pending_hardware_move = False
                    pending_edit_move = False
                    next_step_at = step_seconds
                    print("[gui_driver] reset")

                elif typ == "pause" and running:
                    paused = True
                    print("[gui_driver] paused")

                elif typ == "resume" and running:
                    paused = False
                    print("[gui_driver] resumed")

                elif typ == "step_seconds":
                    try:
                        step_seconds = max(0.1, float(cmd.get("value", step_seconds)))
                        print(f"[gui_driver] step seconds set to {step_seconds}")
                    except Exception:
                        pass

                elif typ == "edit_ball":
                    print("[gui_driver] edit mode enabled")

                elif typ == "done_ball":
                    if pending_hardware_move:
                        print("[gui_driver] Finish or reset the pending move before replacing a path")
                        continue
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

            if running and use_controls and not paused and time.monotonic() >= next_step_at:
                if not pending_hardware_move:
                    if not _refresh_positions(algorithm):
                        paused = True
                        print("[gui_driver] Paused: fresh positions required before planning a move")
                        continue
                    if edit_ball_queue:
                        ball_id, (x, y) = edit_ball_queue[0]
                        if not _set_hardware_edit_target(algorithm, ball_id, x, y):
                            paused = True
                            print("[gui_driver] Paused: edited target is occupied or invalid")
                            continue
                        pending_edit_move = True
                    else:
                        algorithm.bond_all_groups()
                        algorithm.move_all_groups()
                        # The planner reserves its destinations internally. Keep
                        # the displayed/current grid at the unconfirmed starts.
                        _restore_current_grid(algorithm)
                    pending_hardware_move = True

                if controls_sock is None:
                    controls_sock = _connect_controls(port)
                if _drive_to_targets(controls_sock, algorithm, constants, use_algorithm_colors):
                    _commit_targets(algorithm)
                    if pending_edit_move:
                        edit_ball_queue.pop(0)
                    algorithm = _rebond_from_current_positions(algorithm)
                    pending_hardware_move = False
                    pending_edit_move = False
                else:
                    paused = True
                    print("[gui_driver] Paused: move unconfirmed; target retained. "
                          "Check tracking/controls before resuming, or reset and recalibrate.")
                next_step_at = time.monotonic() + step_seconds

            elif not use_controls and not pending_hardware_move:
                # Simulation-only editing and movement do not require a camera.
                if edit_ball_queue:
                    if _process_next_edit_ball_move(algorithm, edit_ball_queue):
                        algorithm = _rebond_from_current_positions(algorithm)
                elif running and not paused and time.monotonic() >= next_step_at:
                    _commit_targets(algorithm)
                    algorithm.bond_all_groups()
                    algorithm.move_all_groups()
                    _commit_targets(algorithm)
                    next_step_at = time.monotonic() + step_seconds

            send_algorithm_state(algorithm)
            time.sleep(0.1)

    except Exception as error:
        print(f"[gui_driver] exception: {error}")
    finally:
        if controls_sock is not None:
            controls_sock.close()

if __name__ == "__main__":
    main_server()
