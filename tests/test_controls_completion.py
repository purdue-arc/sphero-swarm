import importlib
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class ControlsCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("sys.argv", ["controls-test"]):
            cls.server = importlib.import_module("controls.Controls_Server")

    def setUp(self):
        self.server.KILL_FLAG = 0

    def test_completion_is_sent_only_after_commands_finish(self):
        entered, release = threading.Event(), threading.Event()
        command = SimpleNamespace(spheroID=1, type=1)
        batch = {"instructions": [command], "done": threading.Event(), "outcomes": {}}
        def roll(*args):
            entered.set()
            release.wait(2)
        with patch.object(self.server, "run_command", side_effect=roll):
            runner = threading.Thread(target=self.server.run_multi_command, args=([object()], batch))
            runner.start()
            try:
                self.assertTrue(entered.wait(1))
                self.assertFalse(batch["done"].is_set())
            finally:
                release.set()
                runner.join(2)
        self.assertTrue(batch["done"].is_set())
        self.assertEqual(batch["outcomes"], {"1": "complete"})

    def test_disconnected_and_failed_commands_do_not_report_success(self):
        commands = [SimpleNamespace(spheroID=i, type=1) for i in (1, 2)]
        batch = {"instructions": commands, "done": threading.Event(), "outcomes": {}}
        def roll(sb, command):
            if sb is not None:
                raise RuntimeError("Bluetooth disconnected")
        with patch.object(self.server, "run_command", side_effect=roll), self.assertLogs(level="ERROR"):
            self.server.run_multi_command([None, object()], batch)
        self.assertTrue(batch["done"].is_set())
        self.assertEqual(batch["outcomes"], {"1": "disconnected", "2": "failed"})


if __name__ == "__main__":
    unittest.main()
