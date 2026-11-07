"""Square routine: each ball rolls one side, turns 90 degrees, four times, and ends where it started."""
from .base import (
    ROW_SETUP_STEPS, Param, Routine, Slot, colour_batch, roll, row_formation, turn, white_batch,
)

SIDES = 4
TURN_DEGREES = 90
TURN_SECONDS = 0.6

PARAMS = (
    Param("speed", "Speed", 60, 20, 150),
    Param("side_seconds", "Seconds per side", 1.0, 0.3, 3.0),
    Param("spacing_ft", "Spacing (ft)", 3, 1, 8),
)


def _formation(n: int, params: dict) -> list[Slot]:
    return row_formation(n, params["spacing_ft"])


def _batches(n: int, params: dict) -> list[list[dict]]:
    slots = row_formation(n, params["spacing_ft"])
    ids = [slot.slot for slot in slots]
    sides: list[list[dict]] = []
    for _ in range(SIDES):
        sides.append([roll(sphero_id, params["speed"], params["side_seconds"]) for sphero_id in ids])
        sides.append([turn(sphero_id, TURN_DEGREES, TURN_SECONDS) for sphero_id in ids])
    return [colour_batch(slots), *sides, white_batch(ids)]


SQUARE = Routine(
    key="square",
    name="Square",
    description="Balls drive a square one side at a time, turning 90 degrees at each corner.",
    setup_steps=ROW_SETUP_STEPS,
    params=PARAMS,
    build_formation=_formation,
    build_batches=_batches,
)
