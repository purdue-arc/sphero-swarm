"""Routine registry. Adding a routine = one module with a Routine, listed here."""
from typing import Optional

from .base import Routine
from .circle import CIRCLE
from .square import SQUARE

ROUTINES: dict[str, Routine] = {routine.key: routine for routine in (SQUARE, CIRCLE)}


def get(key: str) -> Optional[Routine]:
    return ROUTINES.get(key)
