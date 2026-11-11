import math
import random

from assign import auto_assign, merge_scans, shuffle_assign


def _ball(robot_id, **rssi_by_pi):
    by_pi = {int(pi): rssi for pi, rssi in rssi_by_pi.items()}
    best = max(by_pi, key=lambda pi: (by_pi[pi], -pi), default=None)
    return {"robot_id": robot_id, "rssi_by_pi": by_pi, "best_pi": best}


def _all_ids(assignment):
    return [rid for ids in assignment.values() for rid in ids]


def test_every_pi_is_a_key_even_when_it_gets_nothing():
    merged = [_ball("SB-1", **{"1": -50})]

    assignment = auto_assign(merged, [1, 2, 3])

    assert set(assignment) == {1, 2, 3}
    assert assignment[2] == [] and assignment[3] == []


def test_auto_split_loses_and_duplicates_no_ball_and_respects_ceiling_capacity():
    rng = random.Random(7)
    merged = [_ball(f"SB-{i:02d}", **{str(rng.randint(1, 4)): rng.randint(-90, -40)}) for i in range(10)]

    assignment = auto_assign(merged, [1, 2, 3, 4])

    assert sorted(_all_ids(assignment)) == sorted(row["robot_id"] for row in merged)
    assert max(len(ids) for ids in assignment.values()) <= math.ceil(10 / 4)


def test_ball_goes_to_its_strongest_pi_when_that_pi_has_room():
    merged = [_ball("SB-A", **{"1": -50, "2": -80}), _ball("SB-B", **{"1": -70, "2": -40})]

    assignment = auto_assign(merged, [1, 2])

    assert assignment == {1: ["SB-A"], 2: ["SB-B"]}


def test_ball_heard_by_only_one_pi_goes_there_when_capacity_allows():
    merged = [
        _ball("SB-X", **{"2": -90}),
        _ball("SB-Y", **{"1": -40, "2": -45}),
        _ball("SB-Z", **{"1": -41, "2": -44}),
        _ball("SB-W", **{"1": -42, "2": -43}),
    ]

    assignment = auto_assign(merged, [1, 2])

    assert "SB-X" in assignment[2]
    assert len(assignment[1]) == len(assignment[2]) == 2


def test_auto_assign_with_no_balls_still_returns_every_pi():
    assert auto_assign([], [1, 2]) == {1: [], 2: []}


def test_auto_assign_with_no_pis_returns_empty_mapping():
    assert auto_assign([_ball("SB-1", **{"1": -50})], []) == {}


def test_shuffle_split_sizes_differ_by_at_most_one_and_keep_every_ball():
    rng = random.Random(3)
    for count in range(0, 13):
        ids = [f"SB-{i}" for i in range(count)]

        assignment = shuffle_assign(ids, [1, 2, 3, 4], rng=rng)

        sizes = [len(assignment[pi]) for pi in (1, 2, 3, 4)]
        assert max(sizes) - min(sizes) <= 1
        assert sorted(_all_ids(assignment)) == sorted(ids)


def test_shuffle_does_not_mutate_its_input():
    ids = ["SB-1", "SB-2", "SB-3"]

    shuffle_assign(ids, [1, 2], rng=random.Random(1))

    assert ids == ["SB-1", "SB-2", "SB-3"]


def test_merge_scans_combines_pis_sorts_by_robot_and_breaks_ties_to_lower_pi():
    per_pi = {
        1: [{"robot_id": "SB-2", "rssi": -60}, {"robot_id": "SB-1", "rssi": -50}],
        2: [{"robot_id": "SB-1", "rssi": -50}],
    }

    merged = merge_scans(per_pi)

    assert [row["robot_id"] for row in merged] == ["SB-1", "SB-2"]
    assert merged[0] == {"robot_id": "SB-1", "rssi_by_pi": {1: -50, 2: -50}, "best_pi": 1}
    assert merged[1]["best_pi"] == 1
