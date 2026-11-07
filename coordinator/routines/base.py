"""Shared shapes for routines: parameters, the row formation, and instruction builders.

A routine is data in, data out. Given a robot count and parameters it returns
where each ball starts (formation) and the batches of instruction dicts that
BatchExecutor runs in order. Instruction dicts use the Pi /command field
names (docs/swarm-control.md, Contract 1), so they can go straight to a Pi.
"""
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable

SLOT_COLORS: tuple[tuple[int, int, int], ...] = (
    (230, 25, 75),    # red
    (60, 180, 75),    # green
    (255, 225, 25),   # yellow
    (0, 130, 200),    # blue
    (245, 130, 48),   # orange
    (145, 30, 180),   # purple
    (70, 240, 240),   # cyan
    (240, 50, 230),   # magenta
    (191, 239, 69),   # lime
    (250, 190, 212),  # pink
)
WHITE = (255, 255, 255)

ROW_SETUP_STEPS: tuple[str, ...] = (
    "Place the balls in a row, left to right in slot order, about {spacing_ft} ft apart, "
    "with clear space ahead of and to the right of the row.",
    "Click Identify, then swap balls until each ball's colour matches its slot in the diagram.",
    "Click Aim on, rotate each ball by hand so its blue back light points at you, then click Aim done.",
    "Click Run.",
)


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    default: float | int
    min: float | int
    max: float | int


@dataclass(frozen=True)
class Slot:
    slot: int
    x_ft: float
    y_ft: float
    heading_deg: float
    color: tuple[int, int, int]


Params = dict[str, float | int]
Formation = Callable[[int, Params], list[Slot]]
Batches = Callable[[int, Params], list[list[dict]]]


@dataclass(frozen=True)
class Routine:
    key: str
    name: str
    description: str
    setup_steps: tuple[str, ...]
    params: tuple[Param, ...]
    build_formation: Formation
    build_batches: Batches
    min_robots: int = 1
    max_robots: int = 10

    def resolve(self, given: Mapping | None = None) -> Params:
        return resolve_params(self.params, given)

    def formation(self, n: int, given: Mapping | None = None) -> list[Slot]:
        self._check_count(n)
        return self.build_formation(n, self.resolve(given))

    def batches(self, n: int, given: Mapping | None = None) -> list[list[dict]]:
        self._check_count(n)
        return self.build_batches(n, self.resolve(given))

    def setup_text(self, given: Mapping | None = None) -> tuple[str, ...]:
        params = self.resolve(given)
        return tuple(step.format(**params) for step in self.setup_steps)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "setup_steps": list(self.setup_text()),
            "min_robots": self.min_robots,
            "max_robots": self.max_robots,
            "params": [
                {"name": p.name, "label": p.label, "default": p.default, "min": p.min, "max": p.max}
                for p in self.params
            ],
        }

    def _check_count(self, n: int) -> None:
        if not self.min_robots <= n <= self.max_robots:
            raise ValueError(f"{self.name} needs {self.min_robots}-{self.max_robots} robots, got {n}")


def resolve_params(params: tuple[Param, ...], given: Mapping | None) -> Params:
    """Fill in defaults, coerce to number, and clamp to each param's range.

    Unknown keys are ignored. A value that is missing or not a finite number
    falls back to the default instead of failing the request.
    """
    given = given or {}
    resolved: Params = {}
    for param in params:
        value = _as_number(given.get(param.name), param.default)
        clamped = min(max(value, param.min), param.max)
        resolved[param.name] = int(round(clamped)) if isinstance(param.default, int) else float(clamped)
    return resolved


def _as_number(value, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return number if math.isfinite(number) else float(fallback)


def row_formation(n: int, spacing_ft: float) -> list[Slot]:
    """Balls in one row, left to right, all facing away from the operator (heading 0)."""
    return [
        Slot(slot=index + 1, x_ft=index * spacing_ft, y_ft=0.0, heading_deg=0.0,
             color=SLOT_COLORS[index % len(SLOT_COLORS)])
        for index in range(n)
    ]


def colour_batch(slots: list[Slot]) -> list[dict]:
    return [led(slot.slot, *slot.color) for slot in slots]


def white_batch(sphero_ids: list[int]) -> list[dict]:
    return [led(sphero_id, *WHITE) for sphero_id in sphero_ids]


def led(sphero_id: int, r: int, g: int, b: int) -> dict:
    return {"spheroID": sphero_id, "type": 0, "r": r, "g": g, "b": b}


def roll(sphero_id: int, speed: float, seconds: float) -> dict:
    return {"spheroID": sphero_id, "type": 1, "speed": speed, "duration": seconds}


def turn(sphero_id: int, degrees: float, seconds: float) -> dict:
    return {"spheroID": sphero_id, "type": 2, "degrees": degrees, "duration": seconds}
