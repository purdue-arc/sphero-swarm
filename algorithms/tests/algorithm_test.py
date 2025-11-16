import pytest
from algorithm import Algorithm
from sphero import Sphero
from constants import *
from typing import List, Tuple

def create_algorithm(
    grid_width: int = 5,
    grid_height: int = 5,
    n_spheros: int = 2,
    colors: List[Tuple[int, int, int]] = None,
    initial_positions: List[int] = None,
):
    return Algorithm(grid_width=grid_width,
                     grid_height=grid_height, 
                     n_spheros=n_spheros,
                     colors=colors,
                     initial_positions=initial_positions,
                     )

def test_is_valid_move(
    algorithm: Algorithm = None,
    direction: int = None,
    sphero: Sphero = None,
    is_valid: bool = True
):
    assert algorithm.is_valid_move(direction=direction, sphero=sphero) == is_valid

def test_moveset(
    initial_positions: List[Tuple[int, int]],
    directions: List[List[int]]
):
    algorithm = create_algorithm(initial_positions=initial_positions)

    for sphero_directions in directions:
        for direction in sphero_directions:
            test_is_valid_move(algorithm=algorithm, direction=direction)
    
    # Check target positions
    assert spheros[0].compute_target_position(1) == (0, 1)
    assert spheros[1].compute_target_position(8) == (1, 1)

    # Check valid moves
    assert algorithm.is_valid_move(direction=1, sphero=spheros[0])
    assert algorithm.is_valid_move(direction=8, sphero=spheros[1])

    # Move spheros and update nodes
    spheros[0].update_movement(1)
    spheros[1].update_movement(8)
    algorithm.update_nodes(spheros[0])
    algorithm.update_nodes(spheros[1])

    assert algorithm.nodes[0][1] == 1
    assert algorithm.nodes[1][1] == 2
    assert algorithm.nodes[0][0] == 0
    assert algorithm.nodes[2][0] == 0

def test_second_move_set(algorithm):
    positions_directions = [
        (0, 1, 1, 2),  # Sphero 1 at (0,1) moving direction 2
        (1, 1, 2, 6)   # Sphero 2 at (1,1) moving direction 6
    ]
    spheros = setup_spheros(algorithm, positions_directions)

    assert spheros[0].compute_target_position(2) == (1, 2)
    assert spheros[1].compute_target_position(6) == (0, 0)

def test_third_move_set(algorithm):
    positions_directions = [
        (1, 2, 1, 3),  # Sphero 1 at (1,2) moving direction 3
        (0, 0, 2, 3)   # Sphero 2 at (0,0) moving direction 3
    ]
    spheros = setup_spheros(algorithm, positions_directions)

    assert spheros[0].compute_target_position(3) == (2, 2)
    assert spheros[1].compute_target_position(3) == (1, 0)


# TODO:
# Jay: Work on a general test case for the bonding test case for n many spheros and a list of directions and see if the spheros bond correctly. TEST update_sphero_bonds
#