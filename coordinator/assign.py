"""Pure assignment logic: which Pi should own which ball.

Kept free of I/O so the dashboard's auto/shuffle buttons can be tested
without Pis. Every Pi number is a key in the result (possibly empty) because
an empty list is how the coordinator tells a Pi to release everything it
holds.
"""
import math
import random
from typing import Iterable, Optional

UNHEARD_RSSI = -1000


def merge_scans(per_pi: dict[int, list[dict]]) -> list[dict]:
    """Combine each Pi's /scan results into one row per ball, sorted by robot_id."""
    heard: dict[str, dict[int, int]] = {}
    for pi_number, robots in per_pi.items():
        for robot in robots:
            rssi = robot.get("rssi")
            if rssi is None:
                continue
            by_pi = heard.setdefault(robot["robot_id"], {})
            by_pi[pi_number] = max(rssi, by_pi.get(pi_number, rssi))
    return [_merged_row(robot_id, heard[robot_id]) for robot_id in sorted(heard)]


def auto_assign(merged: list[dict], pi_numbers: Iterable[int]) -> dict[int, list[str]]:
    """Even split (sizes differ by at most ceil(n/k)) that prefers the strongest signal.

    Balls heard by the fewest Pis go first, so the hard-to-place ones get a
    choice while there is still room. Each ball goes to its best-signal Pi if
    that Pi has room, else the least-loaded Pi that heard it, else the
    least-loaded Pi overall.
    """
    pis = list(pi_numbers)
    assignment: dict[int, list[str]] = {pi: [] for pi in pis}
    if not pis:
        return assignment
    capacity = math.ceil(len(merged) / len(pis))
    for ball in sorted(merged, key=lambda row: _priority(row, pis)):
        pi = _choose_pi(ball, assignment, capacity)
        assignment[pi].append(ball["robot_id"])
    return assignment


def shuffle_assign(robot_ids: Iterable[str], pi_numbers: Iterable[int],
                   rng: Optional[random.Random] = None) -> dict[int, list[str]]:
    """Random even split. Sizes differ by at most one. The input list is not mutated."""
    rng = rng or random.Random()
    pis = list(pi_numbers)
    ids = list(robot_ids)
    rng.shuffle(ids)
    assignment: dict[int, list[str]] = {pi: [] for pi in pis}
    if not pis:
        return assignment
    base, extra = divmod(len(ids), len(pis))
    start = 0
    for index, pi in enumerate(pis):
        size = base + (1 if index < extra else 0)
        assignment[pi] = ids[start:start + size]
        start += size
    return assignment


def _merged_row(robot_id: str, by_pi: dict[int, int]) -> dict:
    ordered = {pi: by_pi[pi] for pi in sorted(by_pi)}
    return {"robot_id": robot_id, "rssi_by_pi": ordered, "best_pi": _best_pi(ordered)}


def _best_pi(rssi_by_pi: dict[int, int]) -> Optional[int]:
    return max(rssi_by_pi, key=lambda pi: (rssi_by_pi[pi], -pi), default=None)


def _heard(ball: dict, pis: Iterable[int]) -> dict[int, int]:
    allowed = set(pis)
    return {pi: rssi for pi, rssi in ball["rssi_by_pi"].items() if pi in allowed}


def _priority(ball: dict, pis: list[int]) -> tuple:
    heard = _heard(ball, pis)
    strongest = max(heard.values(), default=UNHEARD_RSSI)
    return (len(heard), -strongest, ball["robot_id"])


def _choose_pi(ball: dict, assignment: dict[int, list[str]], capacity: int) -> int:
    def has_room(pi: int) -> bool:
        return len(assignment[pi]) < capacity

    heard = _heard(ball, assignment.keys())
    best = _best_pi(heard)
    if best is not None and has_room(best):
        return best
    heard_with_room = [pi for pi in heard if has_room(pi)]
    if heard_with_room:
        return min(heard_with_room, key=lambda pi: (len(assignment[pi]), -heard[pi], pi))
    return min((pi for pi in assignment if has_room(pi)), key=lambda pi: (len(assignment[pi]), pi))
