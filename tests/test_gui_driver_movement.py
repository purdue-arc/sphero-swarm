import time
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from tempfile import TemporaryDirectory
from pathlib import Path
from perception.roll_evaluation import RollEvaluation
from perception.grid_geometry import NODE_SPACING_INCHES, GRID_PADDING_INCHES

from algorithms.algorithm import Algorithm
from algorithms.constants import constants
from algorithms.sphero import Sphero
with patch("threading.Thread.start"):
    import gui_driver


class MovementStrategyTests(unittest.TestCase):
    def test_movement_and_perception_use_the_same_physical_grid(self):
        self.assertEqual(constants.NODE_SPACING_INCHES, NODE_SPACING_INCHES)
        self.assertEqual(gui_driver.ROLL_STRAIGHT_INCH, NODE_SPACING_INCHES)
        self.assertEqual(constants.GRID_PADDING_INCHES, GRID_PADDING_INCHES)

    def setUp(self):
        self.sphero = Sphero(1, 0, 0)
        self.algorithm = Algorithm(5, 5, [self.sphero])
        self.sphero.has_perception_measurement = True
        self.sphero.measurement_timestamp = time.time()
        self.sphero.measurement_stale = False
        self.sphero.true_x, self.sphero.true_y = 0.5, 0
        self.sphero.prev_true_x, self.sphero.prev_true_y = 0.5, 0
        self.sphero.target_x, self.sphero.target_y = 2, 0
        self.sphero.delta_angle = 12

    def perception_reply(self, message):
        if message["action"] == "roll_targets":
            self.targets = message["targets"]
            return {"ok": True}
        if message["action"] == "roll_results":
            return {"finished": True, "trials": [dict(t, status="settled", passed=True)
                                                  for t in self.targets]}
        return {"ok": True}

    def test_default_uses_measured_distance_and_reports_actual_roll(self):
        batches = []
        def send(sock, instructions):
            batches.append(instructions)
            return {"1": "complete"}
        with patch.object(gui_driver, "send_batch", side_effect=send), patch.object(
            gui_driver, "_perception_request", side_effect=self.perception_reply
        ) as perception:
            gui_driver._send_controls_update(None, self.algorithm, constants, False)
        roll = batches[2][0]
        distance = 1.5 * gui_driver.ROLL_STRAIGHT_INCH
        self.assertEqual(roll.speed, constants.SPHERO_SPEED)
        self.assertAlmostEqual(roll.duration, self.algorithm.get_roll_duration(distance))
        self.assertEqual(batches[1][0].degrees, self.sphero.delta_angle)
        target = self.targets[0]
        self.assertEqual(target["id"], self.sphero.id)
        self.assertEqual(target["speed"], roll.speed)
        self.assertEqual(target["duration"], roll.duration)
        self.assertAlmostEqual(target["distance"], distance)

    def test_speed_strategy_can_be_selected(self):
        with patch.object(gui_driver, "send_batch", return_value={"1": "complete"}) as send, patch.object(
            gui_driver, "_perception_request", side_effect=self.perception_reply
        ):
            gui_driver._send_controls_update(
                None, self.algorithm, constants, False,
                roll_strategy=gui_driver._speed_based_roll,
            )
        roll = send.call_args_list[2].args[1][0]
        self.assertEqual(roll.speed, self.algorithm.calculate_speed(self.sphero))
        self.assertEqual(roll.duration, constants.ROLL_DURATION)

    def test_both_strategies_skip_missing_stale_and_at_target_measurements(self):
        for strategy in (gui_driver._distance_based_roll, gui_driver._speed_based_roll):
            for state in ("missing", "old", "stale", "at_target"):
                with self.subTest(strategy=strategy.__name__, state=state):
                    self.setUp()
                    if state == "missing":
                        self.sphero.has_perception_measurement = False
                    elif state == "old":
                        self.sphero.measurement_timestamp -= constants.MAX_PERCEPTION_AGE + 1
                    elif state == "stale":
                        self.sphero.measurement_stale = True
                    else:
                        self.sphero.true_x = self.sphero.target_x
                    with patch.object(gui_driver, "send_batch", return_value={}) as send, patch.object(
                        gui_driver, "_perception_request"
                    ) as perception:
                        gui_driver._send_controls_update(
                            None, self.algorithm, constants, False, roll_strategy=strategy
                        )
                    self.assertTrue(all(i.type != 1 for c in send.call_args_list for i in c.args[1]))
                    perception.assert_not_called()

    def test_first_roll_turns_from_calibrated_forward(self):
        with patch.object(gui_driver, "send_batch", return_value={"1": "complete"}) as send, patch.object(
            gui_driver, "_perception_request", side_effect=self.perception_reply
        ):
            gui_driver._send_controls_update(None, self.algorithm, constants, False)
        self.assertEqual(send.call_args_list[1].args[1][0].degrees, -90)
        self.assertEqual(self.sphero.heading_angle, 0)
        # No measured travel yet: the next turn must use the acknowledged heading.
        self.sphero.target_x, self.sphero.target_y = 0.5, 1
        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero), 90)

    def test_failed_turn_does_not_update_heading_or_roll(self):
        with patch.object(gui_driver, "send_batch", return_value={"1": "failed"}) as send, patch.object(
            gui_driver, "_perception_request", side_effect=self.perception_reply
        ):
            result = gui_driver._send_controls_update(None, self.algorithm, constants, False)
        self.assertEqual(result, "failed")
        self.assertEqual(self.sphero.heading_angle, 90)
        self.assertFalse(self.sphero.heading_valid)
        self.assertEqual(send.call_count, 2)

    def test_evaluation_unavailable_withholds_turn_and_roll(self):
        with patch.object(gui_driver, "send_batch") as send, patch.object(
            gui_driver, "_perception_request", return_value=None
        ):
            self.assertEqual(gui_driver._send_controls_update(None, self.algorithm, constants, False), "failed")
        self.assertEqual(send.call_count, 1)
        self.assertTrue(all(i.type == 0 for i in send.call_args.args[1]))

    def test_evaluation_matches_each_robot_to_its_own_camera_detection(self):
        second = Sphero(2, 3, 3)
        second.has_perception_measurement = True
        second.measurement_stale = False
        second.measurement_timestamp = time.time()
        second.target_x = 4
        algorithm = Algorithm(5, 5, [self.sphero, second])
        targets = []
        def perception(message):
            if message["action"] == "roll_targets":
                targets.extend(message["targets"])
                return {"ok": True}
            if message["action"] == "roll_results":
                return {"finished": True, "trials": [dict(t, status="settled", passed=True) for t in targets]}
            return {"ok": True}
        with patch.object(gui_driver, "send_batch", return_value={"1": "complete", "2": "complete"}), patch.object(
            gui_driver, "_perception_request", side_effect=perception
        ):
            gui_driver._send_controls_update(None, algorithm, constants, False)
        with TemporaryDirectory() as folder:
            evaluator = RollEvaluation(Path(folder) / "rolls.csv")
            now = time.time()
            evaluator.update({1: (0.5, 0), 2: (3, 3)}, now, now)
            evaluator.start(targets, now)
            self.assertEqual(evaluator.trials[1]["start"], (0.5, 0))
            self.assertEqual(evaluator.trials[2]["start"], (3, 3))
            self.assertNotIn(0, evaluator.trials)

    def test_retries_keep_target_and_positions_until_arrival(self):
        targets = []
        def send(*args):
            targets.append((self.sphero.target_x, self.sphero.target_y))
            return "off_target" if len(targets) == 1 else "complete"
        def refresh(algorithm):
            if len(targets) == 2:
                self.sphero.true_x = self.sphero.target_x
            return True
        with patch.object(gui_driver, "_refresh_positions", side_effect=refresh), patch.object(
            gui_driver, "_send_controls_update", side_effect=send
        ):
            self.assertTrue(gui_driver._drive_to_targets(None, self.algorithm, constants, False))
        self.assertEqual(targets, [(2, 0), (2, 0)])
        self.assertEqual((self.sphero.x, self.sphero.y), (0, 0))
        gui_driver._commit_targets(self.algorithm)
        self.assertEqual((self.sphero.x, self.sphero.y), (2, 0))
        self.assertEqual(self.algorithm.current_grid[2][0], 1)

    def test_failed_stale_or_exhausted_attempts_do_not_commit_positions(self):
        for status in ("failed", "off_target", "stale"):
            with self.subTest(status=status), patch.object(
                gui_driver, "_refresh_positions", return_value=status != "stale"
            ), patch.object(gui_driver, "_send_controls_update", return_value=status) as send:
                self.assertFalse(gui_driver._drive_to_targets(None, self.algorithm, constants, False))
                self.assertEqual(send.call_count, 3 if status == "off_target" else 0 if status == "stale" else 1)
                self.assertEqual((self.sphero.x, self.sphero.y), (0, 0))
                self.assertEqual((self.sphero.target_x, self.sphero.target_y), (2, 0))

    def test_edit_target_and_rebond_preserve_heading_and_measurements(self):
        self.sphero.heading_angle = 35
        rebuilt = gui_driver._rebond_from_current_positions(self.algorithm)
        self.assertIs(rebuilt.find_sphero(1), self.sphero)
        self.assertTrue(gui_driver._set_hardware_edit_target(rebuilt, 1, 1, 1))
        self.assertEqual((self.sphero.x, self.sphero.y), (0, 0))
        self.assertEqual(self.sphero.heading_angle, 35)
        self.assertTrue(self.sphero.has_perception_measurement)
        self.assertIsNotNone(gui_driver._distance_based_roll(rebuilt, self.sphero, constants))

    def test_stationary_plan_turns_toward_physical_position_error(self):
        self.sphero.target_x, self.sphero.target_y = 0, 0
        self.sphero.true_x, self.sphero.true_y = 0.5, 0.5
        self.sphero.prev_true_x, self.sphero.prev_true_y = 0.5, 0.5
        with patch.object(gui_driver, "send_batch", return_value={"1": "complete"}) as send, patch.object(
            gui_driver, "_perception_request", side_effect=self.perception_reply
        ):
            gui_driver._send_controls_update(None, self.algorithm, constants, False)
        self.assertEqual(send.call_args_list[1].args[1][0].degrees, 135)
        self.assertEqual(send.call_args_list[2].args[1][0].type, 1)

    def test_main_loop_keeps_failed_target_on_resume_then_commits_after_confirmation(self):
        class StopLoop(BaseException):
            pass
        snapshots = []
        attempts = []
        def plan():
            self.sphero.target_x, self.sphero.target_y = 2, 0
            self.algorithm.current_grid[0][0] = 0
            self.algorithm.current_grid[2][0] = 1
        def drive(*args):
            attempts.append((self.sphero.x, self.sphero.target_x))
            return len(attempts) == 2
        commands = [{"type": "use_controls", "value": True}, {"type": "start"},
                    {"type": "use_controls", "value": False},
                    {"type": "use_controls", "value": True},
                    {"type": "resume"}, StopLoop()]
        with patch.object(gui_driver, "get_next_command", side_effect=commands), patch.object(
            gui_driver, "Constants", return_value=constants
        ), patch.object(gui_driver, "_build_algorithm", return_value=self.algorithm), patch.object(
            gui_driver, "_connect_controls", return_value=Mock()
        ), patch.object(gui_driver, "_refresh_positions", return_value=True), patch.object(
            gui_driver, "_drive_to_targets", side_effect=drive
        ), patch.object(self.algorithm, "move_all_groups", side_effect=plan) as planner, patch.object(
            gui_driver, "send_algorithm_state", side_effect=lambda a: snapshots.append((
                a.find_sphero(1).x, a.current_grid[0][0], a.current_grid[2][0]))
        ), patch.object(gui_driver.time, "monotonic", side_effect=[100, 100, 105, 105]), patch.object(
            gui_driver.time, "sleep"
        ), self.assertRaises(StopLoop):
            gui_driver.main_server()
        self.assertEqual(planner.call_count, 1)
        self.assertEqual(attempts, [(0, 2), (0, 2)])
        self.assertEqual(snapshots, [(0, 1, 0)] * 4 + [(2, 0, 1)])

    def test_main_loop_keeps_edited_waypoint_until_confirmed(self):
        class StopLoop(BaseException):
            pass
        clock = [1]
        commands = iter([
            {"type": "start"}, {"type": "use_controls", "value": True},
            {"type": "done_ball", "ball_id": 1,
             "path": [{"x": 1, "y": 1}, {"x": 2, "y": 1}]}, {"type": "resume"},
        ])
        stamps = iter([1, 1, 10, 15])
        attempts = []
        def command(**kwargs):
            try:
                clock[0] = next(stamps)
                return next(commands)
            except StopIteration:
                raise StopLoop()
        def drive(sock, algorithm, *args):
            s = algorithm.find_sphero(1)
            attempts.append((s.x, s.y, s.target_x, s.target_y, s.has_perception_measurement))
            return len(attempts) == 2
        with patch.object(gui_driver, "get_next_command", side_effect=command), patch.object(
            gui_driver, "Constants", return_value=constants
        ), patch.object(gui_driver, "_build_algorithm", return_value=self.algorithm), patch.object(
            gui_driver, "_connect_controls", return_value=Mock()
        ), patch.object(gui_driver, "_refresh_positions", return_value=True), patch.object(
            gui_driver, "_drive_to_targets", side_effect=drive
        ), patch.object(self.algorithm, "move_all_groups") as planner, patch.object(
            gui_driver, "send_algorithm_state"
        ), patch.object(gui_driver.time, "monotonic", side_effect=lambda: clock[0]), patch.object(
            gui_driver.time, "sleep"
        ), self.assertRaises(StopLoop):
            gui_driver.main_server()
        planner.assert_not_called()
        self.assertEqual(attempts, [(0, 0, 1, 1, True), (0, 0, 1, 1, True)])
        self.assertEqual((self.sphero.x, self.sphero.y), (1, 1))


if __name__ == "__main__":
    unittest.main()
