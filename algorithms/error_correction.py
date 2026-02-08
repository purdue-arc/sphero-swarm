import numpy as np
from typing import Tuple

def error_correction_vector(actual: Tuple[int, int],
                             next: Tuple[int, int]):
    """
    Generates a vector to move from the sphero's actual position
    to the next chosen position

    Args:
        actual (Tuple[int, int]): Actual position.
        next (Tuple[int, int]): Next chosen position.

    Returns:
        Tuple[float, float]: degrees and magnitude of correction vector
    """
    nextv = np.array([next[0], next[1]]).astype(float)
    actualv = np.array([actual[0], actual[1]]).astype(float)

    d = np.dot(nextv, actualv)
    theta = np.arccos(d/ (np.linalg.norm(nextv) * np.linalg.norm(actualv)))
    theta = np.round(theta * (180 / np.pi))

    degnext = np.arctan2(nextv[1], nextv[0]) + np.pi
    degact = np.arctan2(actualv[1], actualv[0]) + np.pi

    if (degact - degnext > 0):
        theta *= -1

    magnitude = np.linalg.norm((nextv - actualv))
    return (theta, magnitude)
    