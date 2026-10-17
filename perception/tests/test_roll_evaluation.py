import csv
from pathlib import Path
import tempfile
import unittest

from perception.roll_evaluation import RollEvaluation


class RollEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "rolls.csv"
        self.evaluation = RollEvaluation(self.path)
        self.target = dict(trial_id="trial", algorithm_id=1, id=0, x=2, y=1,
                           duration=0.7, speed=66, distance=12.67)
        self.evaluation.update({0: (1, 1)}, 0, 0)
        self.evaluation.start([self.target], 0.1)

    def settle(self, pos=(2.2, 1.1)):
        self.evaluation.complete("trial", {"1": "complete"}, 1)
        for stamp in (1.1, 1.3, 1.5, 1.7, 1.9):
            self.evaluation.update({0: pos}, stamp, stamp)

    def test_endpoint_error_and_csv_are_measured_from_camera(self):
        self.settle()
        trial = self.evaluation.snapshot()[0]
        self.assertEqual(trial["status"], "settled")
        self.assertAlmostEqual(trial["error"], (0.2 ** 2 + 0.1 ** 2) ** 0.5)
        self.assertAlmostEqual(trial["along_error"], 0.2)
        self.assertAlmostEqual(trial["lateral_error"], 0.1)
        self.assertFalse(trial["passed"])
        with self.path.open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(float(rows[0]["error_inches"]), trial["error"] * 12.67)
        self.evaluation.update({0: (3, 3)}, 2, 2)
        self.assertEqual(self.evaluation.snapshot()[0]["endpoint"], trial["endpoint"])

    def test_stale_and_missing_detections_never_become_endpoints(self):
        self.evaluation.complete("trial", {"1": "complete"}, 1)
        for stamp in (2, 3, 4, 5, 6):
            self.evaluation.update({0: (2, 1)}, stamp - 1, stamp)
        self.evaluation.update({}, 11, 11)
        trial = self.evaluation.snapshot()[0]
        self.assertEqual(trial["status"], "timeout")
        self.assertIsNone(trial["endpoint"])

    def test_motion_and_tracking_gaps_restart_stability_window(self):
        self.evaluation.complete("trial", {"1": "complete"}, 1)
        for stamp, pos in ((1.1, (1, 1)), (1.3, (1.3, 1)), (1.5, (1.6, 1))):
            self.evaluation.update({0: pos}, stamp, stamp)
        self.evaluation.update({}, 1.7, 1.7)
        for stamp in (1.9, 2.1, 2.3, 2.5):
            self.evaluation.update({0: (2, 1)}, stamp, stamp)
        self.assertEqual(self.evaluation.snapshot()[0]["status"], "settling")
        self.evaluation.update({0: (2, 1)}, 2.7, 2.7)
        self.assertTrue(self.evaluation.snapshot()[0]["passed"])

    def test_failed_controls_and_missing_start_are_flagged(self):
        self.evaluation.complete("trial", {"1": "disconnected"}, 1)
        self.assertEqual(self.evaluation.snapshot()[0]["status"], "controls_failed")
        self.evaluation.latest = {}
        self.evaluation.start([self.target], 0.1)
        self.settle()
        self.assertEqual(self.evaluation.snapshot()[0]["status"], "missing_start")

    def test_wrong_trial_completion_is_ignored(self):
        self.evaluation.complete("old", {"1": "complete"}, 1)
        self.assertEqual(self.evaluation.snapshot()[0]["status"], "rolling")


if __name__ == "__main__":
    unittest.main()
