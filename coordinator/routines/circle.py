"""Circle routine: balls drive a polygon that approximates a circle, one lap in total."""
from .base import (
    ROW_SETUP_STEPS, Param, Routine, Slot, colour_batch, roll, row_formation, turn, white_batch,
)

TURN_SECONDS = 0.2

PARAMS = (
    Param("speed", "Speed", 50, 20, 150),
    Param("lap_seconds", "Seconds per lap", 4.0, 2.0, 10.0),
    Param("segments", "Segments", 12, 6, 24),
    Param("spacing_ft", "Spacing (ft)", 3, 1, 8),
)


def _formation(n: int, params: dict) -> list[Slot]:
    return row_formation(n, params["spacing_ft"])


def _batches(n: int, params: dict) -> list[list[dict]]:
    slots = row_formation(n, params["spacing_ft"])
    ids = [slot.slot for slot in slots]
    segments = params["segments"]
    segment_seconds = params["lap_seconds"] / segments
    steps: list[list[dict]] = []
    for i in range(segments):
        # Whole-degree turns (the ball only takes whole degrees) that still sum to
        # exactly 360, e.g. 7 segments -> 51/52/51/... instead of 7 x 51 = 357.
        turn_degrees = round(360 * (i + 1) / segments) - round(360 * i / segments)
        steps.append([roll(sphero_id, params["speed"], segment_seconds) for sphero_id in ids])
        steps.append([turn(sphero_id, turn_degrees, TURN_SECONDS) for sphero_id in ids])
    return [colour_batch(slots), *steps, white_batch(ids)]


CIRCLE = Routine(
    key="circle",
    name="Circle",
    description="Balls drive a circle in equal segments, turning a little at each step.",
    setup_steps=ROW_SETUP_STEPS,
    params=PARAMS,
    build_formation=_formation,
    build_batches=_batches,
)
