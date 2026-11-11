import pytest

from routines import ROUTINES, get
from routines.base import SLOT_COLORS, resolve_params
from routines.circle import CIRCLE
from routines.square import SQUARE


def _types(batch):
    return {instruction["type"] for instruction in batch}


def test_square_batch_shape_is_colours_then_four_sides_then_white():
    batches = SQUARE.batches(3, {})

    assert len(batches) == 1 + 4 * 2 + 1
    assert _types(batches[0]) == {0}
    assert [b[0]["type"] for b in batches[1:-1]] == [1, 2] * 4
    assert _types(batches[-1]) == {0}
    assert all((i["r"], i["g"], i["b"]) == (255, 255, 255) for i in batches[-1])


def test_square_rolls_and_turns_use_contract_fields_for_every_ball():
    batches = SQUARE.batches(2, {"speed": 80, "side_seconds": 1.5})

    roll = batches[1]
    turn = batches[2]
    assert roll == [
        {"spheroID": 1, "type": 1, "speed": 80, "duration": 1.5},
        {"spheroID": 2, "type": 1, "speed": 80, "duration": 1.5},
    ]
    assert turn == [
        {"spheroID": 1, "type": 2, "degrees": 90, "duration": 0.6},
        {"spheroID": 2, "type": 2, "degrees": 90, "duration": 0.6},
    ]


def test_circle_segments_split_the_lap_and_turn_the_full_circle():
    batches = CIRCLE.batches(1, {"lap_seconds": 6.0, "segments": 6, "speed": 50})

    assert len(batches) == 1 + 6 * 2 + 1
    roll = batches[1][0]
    turn = batches[2][0]
    assert roll["duration"] == pytest.approx(1.0)
    assert roll["speed"] == 50
    assert turn["type"] == 2
    assert turn["degrees"] == pytest.approx(60.0)


@pytest.mark.parametrize("segments", [6, 7, 11, 13, 24])
def test_circle_turns_are_whole_degrees_summing_to_360(segments):
    batches = CIRCLE.batches(1, {"lap_seconds": 6.0, "segments": segments, "speed": 50})
    turns = [batch[0]["degrees"] for batch in batches if batch[0]["type"] == 2]
    assert len(turns) == segments
    assert all(float(t).is_integer() for t in turns)
    assert sum(turns) == 360


def test_parameters_are_clamped_to_their_range():
    resolved = resolve_params(SQUARE.params, {"speed": 999, "side_seconds": -1, "spacing_ft": 50})

    assert resolved == {"speed": 150, "side_seconds": 0.3, "spacing_ft": 8}


def test_integer_parameters_stay_integers_and_bad_values_fall_back_to_defaults():
    resolved = resolve_params(CIRCLE.params, {"segments": 100, "speed": "fast", "lap_seconds": float("nan")})

    assert resolved["segments"] == 24 and isinstance(resolved["segments"], int)
    assert resolved["speed"] == 50
    assert resolved["lap_seconds"] == 4.0


def test_unknown_parameter_keys_are_ignored():
    assert "bogus" not in resolve_params(SQUARE.params, {"bogus": 1})


def test_formation_is_a_row_with_distinct_colours_facing_away():
    slots = SQUARE.formation(4, {"spacing_ft": 3})

    assert [s.slot for s in slots] == [1, 2, 3, 4]
    assert [s.x_ft for s in slots] == [0, 3, 6, 9]
    assert all(s.y_ft == 0 and s.heading_deg == 0 for s in slots)
    assert len({s.color for s in slots}) == 4


def test_slot_colours_are_ten_distinct_colours_so_every_allowed_robot_gets_its_own():
    assert len(SLOT_COLORS) == 10 and len(set(SLOT_COLORS)) == 10
    slots = CIRCLE.formation(CIRCLE.max_robots, {})
    assert len({s.color for s in slots}) == CIRCLE.max_robots


@pytest.mark.parametrize("routine", [SQUARE, CIRCLE])
def test_robot_count_outside_range_is_rejected(routine):
    with pytest.raises(ValueError):
        routine.batches(0)
    with pytest.raises(ValueError):
        routine.formation(routine.max_robots + 1)


def test_registry_lookup_and_dict_shape():
    assert get("square") is SQUARE
    assert get("circle") is CIRCLE
    assert get("spiral") is None
    assert set(ROUTINES) == {"square", "circle"}

    described = SQUARE.to_dict()

    assert described["min_robots"] == 1 and described["max_robots"] == 10
    assert any("3 ft apart" in step for step in described["setup_steps"])
    assert [p["name"] for p in described["params"]] == ["speed", "side_seconds", "spacing_ft"]
