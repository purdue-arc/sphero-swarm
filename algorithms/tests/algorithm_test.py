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
    return Algorithm(
        grid_width=grid_width,
        grid_height=grid_height, 
        n_spheros=n_spheros,
        colors=colors,
        initial_positions=initial_positions,
        )

def test_is_valid_move(
    algorithm: Algorithm = None,
    direction: int = None,
    sphero: Sphero = None,
    is_valid: bool = True,
):
    assert algorithm.is_valid_move(direction=direction, sphero=sphero) == is_valid

def test_moveset(
    algorithm: Algorithm,
    initial_positions: List[Tuple[int, int]],
    moveset: List[List[int]],
    bonded_groups_state: List[List[List[int]]], #TODO: BETTER NAME
):
    for i in range(len(moveset)):
        if algorithm.n_spheros != len(moveset[i]):
            raise ValueError(f"Number of moves in moveset {i} doesn't match number of spheros")
        if algorithm.n_spheros != len(bonded_groups_state[i]):
            raise ValueError(f"Number of bonded groups {i} doesn't match number of spheros")
    
    if algorithm.n_spheros != len(initial_positions):
        raise ValueError(f"Number of initial positions doesn't match number of spheros")
    
    if len(moveset) != len(bonded_groups_state):
        raise ValueError("Mismatching number of turns between moveset and bonded groups")

    for i in range(len(moveset)):
        for j in range(len(moveset[i])):
            test_is_valid_move(
                algorithm=algorithm, 
                sphero=algorithm.spheros[i], 
                direction=moveset[i][j]
                )
            # make this into a function
            target_x, target_y = algorithm.spheros[i].compute_target_position(direction=moveset[i][j])
            algorithm.spheros[i].update_direction(direction=moveset[i][j])
            algorithm.update_grid_move()
            assert algorithm.nodes[target_x][target_y] == (i + 1)
        # make this into a function
        assert bonded_groups_state[i] == algorithm.swarm.bonded_groups


# TODO:
# Jay: Work on a general test case for the bonding test case for n many spheros and a list of directions and see if the spheros bond correctly. TEST update_sphero_bonds