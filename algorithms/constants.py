import json
import os


class Constants:
    def __init__(self) -> None:
        # CONSTANTS
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
        self.INITIAL_POSITIONS = [(0, 0), (0, 2), (1, 3), (3, 3), (3, 1)]
        
        self._load_constants_from_file()

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
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load constants.json: {e}")

constants = Constants()

# __all__ = ["Constants", "constants"]

# if __name__ == "__main__":
#     test = Constants() 
#     print("sphero speed should be 60: ", test.SPHERO_SPEED)
#     test.update_variable_constants("./documentation/example_constants.json")
#     print("sphero speed (should be 70 not 60): ", test.SPHERO_SPEED) 