import unittest

from algorithms.algorithm import Algorithm
from algorithms.constants import constants
from algorithms.sphero import Sphero


class ErrorCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.original_values = (
            constants.MIN_ACTUAL_MOVEMENT,
            constants.TARGET_TOLERANCE,
            constants.MAX_PERCEPTION_AGE,
            constants.SPHERO_SPEED,
        )
        constants.MIN_ACTUAL_MOVEMENT = 0.1
        constants.TARGET_TOLERANCE = 0.1
        constants.MAX_PERCEPTION_AGE = 1.0
        constants.SPHERO_SPEED = 66

        self.sphero = Sphero(1, 0, 0)
        self.algorithm = Algorithm(4, 4, [self.sphero])

    def tearDown(self):
        (
            constants.MIN_ACTUAL_MOVEMENT,
            constants.TARGET_TOLERANCE,
            constants.MAX_PERCEPTION_AGE,
            constants.SPHERO_SPEED,
        ) = self.original_values

    def set_position(self, x, y, timestamp, generation=0):
        self.algorithm.set_true_positions(
            {
                "spheros": [
                    {
                        "ID": 1,
                        "X": x,
                        "Y": y,
                        "timestamp": timestamp,
                        "tracking_generation": generation,
                    }
                ]
            },
            now=timestamp,
        )

    def test_first_measurement_uses_calibrated_heading(self):
        self.sphero.target_x = 1
        self.set_position(0.25, 0.5, 100.0)

        angle = self.algorithm.calculate_angle_change(self.sphero, now=100.0)

        self.assertEqual(angle, -124)
        self.assertEqual(self.sphero.prev_true_x, 0.25)
        self.assertEqual(self.sphero.prev_true_y, 0.5)
        self.assertEqual(self.sphero.correction_debug["status"], "heading_fallback")

    def test_signed_angle_uses_degrees(self):
        self.set_position(0, 0, 100.0)
        self.set_position(1, 0, 100.1)

        self.sphero.target_x = 1
        self.sphero.target_y = 1
        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=100.1), 90)

    def test_signed_angle_preserves_negative_turn(self):
        self.set_position(0, 1, 100.0)
        self.set_position(1, 1, 100.1)

        self.sphero.target_x = 1
        self.sphero.target_y = 0
        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=100.1), -90)

    def test_stationary_plan_corrects_physical_drift(self):
        self.set_position(0, 0, 100.0)
        self.set_position(1, 0, 100.1)

        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=100.1), 180)
        self.assertEqual(self.sphero.prev_true_x, 1)
        self.assertGreater(self.algorithm.calculate_speed(self.sphero, now=100.1), 0)

    def test_opposite_direction_returns_180_degrees(self):
        self.set_position(0, 0, 100.0)
        self.set_position(1, 0, 100.1)
        self.sphero.x = 1  # Plan a move back to the origin.
        self.sphero.target_x = 0
        self.sphero.target_y = 0

        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=100.1), 180)

    def test_small_movements_accumulate_against_the_same_anchor(self):
        self.set_position(0, 0, 100.0)
        self.sphero.target_x = 1

        self.set_position(0.04, 0, 100.1)
        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=100.1), -90)
        self.assertEqual(self.sphero.prev_true_x, 0)

        self.set_position(0.11, 0, 100.2)
        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=100.2), 0)
        self.assertEqual(self.sphero.prev_true_x, 0.11)
        self.assertEqual(self.sphero.correction_debug["status"], "corrected")

    def test_target_tolerance_stops_turn_and_roll(self):
        self.set_position(0, 0, 100.0)
        self.set_position(0.2, 0, 100.1)
        self.sphero.target_x = 0.25
        self.sphero.target_y = 0

        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=100.1), 0)
        self.assertEqual(self.algorithm.calculate_speed(self.sphero, now=100.1), 0)
        self.assertEqual(self.sphero.correction_debug["status"], "at_target")

    def test_stale_measurement_stops_turn_and_roll(self):
        self.set_position(0, 0, 100.0)
        self.sphero.target_x = 2

        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=102.0), 0)
        self.assertEqual(self.algorithm.calculate_speed(self.sphero, now=102.0), 0)
        self.assertEqual(self.sphero.correction_debug["status"], "stale_measurement")

    def test_reassigned_track_resets_motion_anchor_and_uses_heading(self):
        self.set_position(0, 0, 100.0, generation=0)
        self.set_position(1, 1, 100.1, generation=1)
        self.sphero.target_x = 2
        self.sphero.target_y = 1

        self.assertEqual(self.algorithm.calculate_angle_change(self.sphero, now=100.1), -90)
        self.assertEqual(self.sphero.prev_true_x, 1)
        self.assertEqual(self.sphero.prev_true_y, 1)
        self.assertEqual(self.sphero.correction_debug["status"], "heading_fallback")

    def test_speed_is_clamped_to_sphero_range(self):
        self.set_position(0, 0, 100.0)
        self.sphero.target_x = 10

        self.assertEqual(self.algorithm.calculate_speed(self.sphero, now=100.0), 255)

    def test_simulation_speed_is_preserved_without_perception(self):
        initial_speed = self.sphero.speed

        self.algorithm.move_all_groups()

        self.assertEqual(self.sphero.speed, initial_speed)


if __name__ == "__main__":
    unittest.main()
