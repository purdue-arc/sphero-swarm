import time
import unittest
from unittest.mock import patch

from algorithms.algorithm import Algorithm
from algorithms.constants import constants
from algorithms.sphero import Sphero
with patch("threading.Thread.start"):
    import gui_driver


class MovementStrategyTests(unittest.TestCase):
    def setUp(self):
        self.sphero = Sphero(1, 0, 0)
        self.algorithm = Algorithm(5, 5, [self.sphero])
        self.sphero.has_perception_measurement = True
        self.sphero.measurement_timestamp = time.time()
        self.sphero.measurement_stale = False
        self.sphero.true_x, self.sphero.true_y = 0.5, 0
        self.sphero.target_x, self.sphero.target_y = 2, 0
        self.sphero.delta_angle = 12

    def test_default_uses_measured_distance_and_reports_actual_roll(self):
        batches = []
        def send(sock, instructions):
            batches.append(instructions)
            return {"1": "complete"}
        with patch.object(gui_driver, "send_batch", side_effect=send), patch.object(
            gui_driver, "_perception_request", return_value=None
        ) as perception:
            gui_driver._send_controls_update(None, self.algorithm, constants, False)
        roll = batches[2][0]
        distance = 1.5 * gui_driver.ROLL_STRAIGHT_INCH
        self.assertEqual(roll.speed, constants.SPHERO_SPEED)
        self.assertAlmostEqual(roll.duration, self.algorithm.get_roll_duration(distance))
        self.assertEqual(batches[1][0].degrees, self.sphero.delta_angle)
        target = perception.call_args.args[0]["targets"][0]
        self.assertEqual(target["speed"], roll.speed)
        self.assertEqual(target["duration"], roll.duration)
        self.assertAlmostEqual(target["distance"], distance)

    def test_speed_strategy_can_be_selected(self):
        with patch.object(gui_driver, "send_batch", return_value={"1": "complete"}) as send, patch.object(
            gui_driver, "_perception_request", return_value=None
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


if __name__ == "__main__":
    unittest.main()
