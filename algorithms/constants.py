import json
import os


class Constants:
    def __init__(self) -> None:
        # Core grid and movement constants
        self.MARGIN = 0
        self.DIRECTIONS = 8
        self.ALL_DIRECTIONS = [1, 2, 3, 4, 5, 6, 7, 8]

        self.position_change = {
            0: (0, 0),
            1: (0, 1),
            2: (1, 1),
            3: (1, 0),
            4: (1, -1),
            5: (0, -1),
            6: (-1, -1),
            7: (-1, 0),
            8: (-1, 1),
        }
        self.EPSILON = 0.01

        # Colors
        self.BLUE = (0, 0, 255)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.YELLOW = (255, 255, 0)
        self.PURPLE = (128, 0, 128)
        self.ORANGE = (255, 165, 0)

        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GRAY = (150, 150, 150)

        self.COLORS = [self.BLUE, self.RED, self.GREEN, self.YELLOW, self.PURPLE, self.ORANGE]

        # Runtime-configurable robot and arena values
        self.N_SPHEROS = 2
        self.GRID_WIDTH = 4
        self.GRID_HEIGHT = 4
        self.SPHERO_SPEED = 60
        self.SPHERO_DIAGONAL_SPEED = 76

        self.ROLL_DURATION = 0.8
        self.TURN_DURATION = 0.5

        self.SPHERO_TAGS = [
            "SB-B11D",
            "SB-BD0A",
        ]
        self.INITIAL_POSITIONS = [(0, 0), (0, 2)]

        # Bonding/simulation controls used by algorithm modules
        self.INITIAL_TRAITS = ["head", "tail"]
        self.MAX_MONOMERS = 3
        self.ARC_ROTATION = False
        self.ERROR_CORRECTION = False
        self.SIM_DIST = 50
        self.FRAMES = 60
        self.SPHERO_SIM_RADIUS = 15
        self.SIM_SPEED = 1

        self._load_constants_from_file()
        self._normalize_derived_values()

    def _load_constants_from_file(self) -> None:
        """Automatically load variable constants from constants.json if it exists."""
        variable_fields = {
            "N_SPHEROS",
            "GRID_WIDTH",
            "GRID_HEIGHT",
            "SPHERO_SPEED",
            "SPHERO_DIAGONAL_SPEED",
            "ROLL_DURATION",
            "TURN_DURATION",
            "SPHERO_TAGS",
            "INITIAL_POSITIONS",
            "INITIAL_TRAITS",
            "MAX_MONOMERS",
            "ARC_ROTATION",
            "ERROR_CORRECTION",
            "SIM_DIST",
            "FRAMES",
            "SPHERO_SIM_RADIUS",
            "SIM_SPEED",
        }

        current_dir = os.path.dirname(os.path.abspath(__file__))
        constants_path = os.path.join(current_dir, "../constants.json")

        if not os.path.exists(constants_path):
            return

        try:
            with open(constants_path, "r", encoding="utf-8") as handle:
                updates = json.load(handle)

            for key, value in updates.items():
                if key in variable_fields:
                    setattr(self, key, value)
        except (json.JSONDecodeError, IOError) as error:
            print(f"Warning: Could not load constants.json: {error}")

    def _normalize_derived_values(self) -> None:
        # Keep positions in a tuple format so hashing/equality checks continue to work.
        self.INITIAL_POSITIONS = [tuple(position) for position in self.INITIAL_POSITIONS]

        # Runtime count follows configured positions.
        self.N_SPHEROS = len(self.INITIAL_POSITIONS)

        # Ensure tag/trait arrays always align with N_SPHEROS.
        self.SPHERO_TAGS = list(self.SPHERO_TAGS[: self.N_SPHEROS])
        while len(self.SPHERO_TAGS) < self.N_SPHEROS:
            self.SPHERO_TAGS.append("SB-XXXX")

        self.INITIAL_TRAITS = list(self.INITIAL_TRAITS[: self.N_SPHEROS])
        while len(self.INITIAL_TRAITS) < self.N_SPHEROS:
            self.INITIAL_TRAITS.append("tail")

        # Keep at least one head by default if user provides all tails.
        if self.N_SPHEROS > 0 and "head" not in self.INITIAL_TRAITS:
            self.INITIAL_TRAITS[0] = "head"

    @property
    def SIM_WIDTH(self) -> int:
        return (self.GRID_WIDTH - 1) * self.SIM_DIST

    @property
    def SIM_HEIGHT(self) -> int:
        return (self.GRID_HEIGHT - 1) * self.SIM_DIST


constants = Constants()

MARGIN = constants.MARGIN
DIRECTIONS = constants.DIRECTIONS
ALL_DIRECTIONS = constants.ALL_DIRECTIONS
position_change = constants.position_change
EPSILON = constants.EPSILON

BLUE = constants.BLUE
RED = constants.RED
GREEN = constants.GREEN
YELLOW = constants.YELLOW
PURPLE = constants.PURPLE
ORANGE = constants.ORANGE
BLACK = constants.BLACK
WHITE = constants.WHITE
GRAY = constants.GRAY
COLORS = constants.COLORS

N_SPHEROS = constants.N_SPHEROS
GRID_WIDTH = constants.GRID_WIDTH
GRID_HEIGHT = constants.GRID_HEIGHT
SPHERO_SPEED = constants.SPHERO_SPEED
SPHERO_DIAGONAL_SPEED = constants.SPHERO_DIAGONAL_SPEED
ROLL_DURATION = constants.ROLL_DURATION
TURN_DURATION = constants.TURN_DURATION
SPHERO_TAGS = constants.SPHERO_TAGS
INITIAL_POSITIONS = constants.INITIAL_POSITIONS
INITIAL_TRAITS = constants.INITIAL_TRAITS
MAX_MONOMERS = constants.MAX_MONOMERS
ARC_ROTATION = constants.ARC_ROTATION
ERROR_CORRECTION = constants.ERROR_CORRECTION
SIM_DIST = constants.SIM_DIST
FRAMES = constants.FRAMES
SPHERO_SIM_RADIUS = constants.SPHERO_SIM_RADIUS
SIM_SPEED = constants.SIM_SPEED
SIM_WIDTH = constants.SIM_WIDTH
SIM_HEIGHT = constants.SIM_HEIGHT


# Backward-compatible module attribute access for old callsites importing
# algorithms.constants as a module and reading values directly.
def __getattr__(name: str):
    if hasattr(constants, name):
        return getattr(constants, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "Constants",
    "constants",
    "MARGIN",
    "DIRECTIONS",
    "ALL_DIRECTIONS",
    "position_change",
    "EPSILON",
    "BLUE",
    "RED",
    "GREEN",
    "YELLOW",
    "PURPLE",
    "ORANGE",
    "BLACK",
    "WHITE",
    "GRAY",
    "COLORS",
    "N_SPHEROS",
    "GRID_WIDTH",
    "GRID_HEIGHT",
    "SPHERO_SPEED",
    "SPHERO_DIAGONAL_SPEED",
    "ROLL_DURATION",
    "TURN_DURATION",
    "SPHERO_TAGS",
    "INITIAL_POSITIONS",
    "INITIAL_TRAITS",
    "MAX_MONOMERS",
    "ARC_ROTATION",
    "ERROR_CORRECTION",
    "SIM_DIST",
    "FRAMES",
    "SPHERO_SIM_RADIUS",
    "SIM_SPEED",
    "SIM_WIDTH",
    "SIM_HEIGHT",
]
