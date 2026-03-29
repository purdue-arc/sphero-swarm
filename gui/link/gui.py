import sys
from pathlib import Path

workspace_root = Path(__file__).resolve().parents[2]
sys.path.append(str(workspace_root))

from algorithms.constants import constants
import json

def export_to_json():
    """Export all constants to a JSON-serializable dictionary"""
    state = {
        "MARGIN": constants.MARGIN,
        "DIRECTIONS": constants.DIRECTIONS,
        "ALL_DIRECTIONS": constants.ALL_DIRECTIONS,
        "position_change": {str(k): list(v) for k, v in constants.position_change.items()},
        "N_SPHEROS": constants.N_SPHEROS,
        "GRID_WIDTH": constants.GRID_WIDTH,
        "GRID_HEIGHT": constants.GRID_HEIGHT,
        "SIM_DIST": constants.SIM_DIST,
        "FRAMES": constants.FRAMES,
        "SPHERO_SIM_RADIUS": constants.SPHERO_SIM_RADIUS,
        "SIM_WIDTH": constants.SIM_WIDTH,
        "SIM_HEIGHT": constants.SIM_HEIGHT,
        "EPSILON": constants.EPSILON,
        "SPHERO_SPEED": constants.SPHERO_SPEED,
        "SPHERO_DIAGONAL_SPEED": constants.SPHERO_DIAGONAL_SPEED,
        "ROLL_DURATION": constants.ROLL_DURATION,
        "TURN_DURATION": constants.TURN_DURATION,
        "SIM_SPEED": constants.SIM_SPEED,
        "ARC_ROTATION": constants.ARC_ROTATION,
        "MAX_MONOMERS": constants.MAX_MONOMERS,
        "COLORS": {
            "BLUE": constants.BLUE,
            "RED": constants.RED,
            "GREEN": constants.GREEN,
            "YELLOW": constants.YELLOW,
            "PURPLE": constants.PURPLE,
            "ORANGE": constants.ORANGE,
            "BLACK": constants.BLACK,
            "WHITE": constants.WHITE,
            "GRAY": constants.GRAY,
        },
        "COLORS_ARRAY": constants.COLORS,
        "SPHERO_TAGS": constants.SPHERO_TAGS,
        "INITIAL_POSITIONS": [list(p) for p in constants.INITIAL_POSITIONS],
        "INITIAL_TRAITS": constants.INITIAL_TRAITS,
    }
    return state

if __name__ == "__main__":
    # Export to stdout for Electron to capture
    state = export_to_json()
    print(json.dumps(state, indent=2))