import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from perception.grid_geometry import ConfiguredGrid, GridGeometry


class GridGeometryTests(unittest.TestCase):
    def test_configured_node_counts_and_complete_diagonals(self):
        for width, height in [(4, 4), (6, 3), (2, 2)]:
            with self.subTest(width=width, height=height):
                grid = GridGeometry(width, height)
                lines = grid.lines((10, 20), (509, 319))
                vertical = [line for line in lines if line[0][0] == line[1][0]]
                horizontal = [line for line in lines if line[0][1] == line[1][1]]
                self.assertEqual(len(vertical), width)
                self.assertEqual(len(horizontal), height)
                self.assertEqual(len(lines) - width - height,
                                 2 * (width - 1) * (height - 1))
                self.assertIn(((509, 20), (509, 319)), vertical)
                self.assertIn(((10, 319), (509, 319)), horizontal)
                last_x = vertical[-2][0][0]
                last_y = horizontal[-2][0][1]
                self.assertIn(((last_x, last_y), (509, 319)), lines)
                self.assertIn(((last_x, 319), (509, last_y)), lines)
                for line in lines:
                    for x, y in line:
                        self.assertTrue(10 <= x <= 509 and 20 <= y <= 319)

    def test_reported_coordinates_match_overlay_nodes(self):
        grid = GridGeometry(6, 4)
        bounds = ((10, 20), (509, 319))
        vertical = grid.lines(*bounds)[:grid.width]
        horizontal = grid.lines(*bounds)[grid.width:grid.width + grid.height]
        for x, column in enumerate(vertical):
            for y, row in enumerate(horizontal):
                gx, gy = grid.pixel_to_grid(column[0][0], row[0][1], *bounds)
                self.assertAlmostEqual(gx, x, delta=0.01)
                self.assertAlmostEqual(gy, y, delta=0.01)
        self.assertEqual(grid.pixel_to_grid(-50, -30, *bounds), (0, 0))
        self.assertEqual(grid.pixel_to_grid(999, 999, *bounds), (5, 3))

    def test_live_settings_changes_and_partial_saves(self):
        with tempfile.TemporaryDirectory() as folder, patch(
                "perception.grid_geometry.time.monotonic") as clock:
            clock.return_value = 0
            settings = Path(folder) / "constants.json"
            settings.write_text(json.dumps({"GRID_WIDTH": 5, "GRID_HEIGHT": 3}))
            grid = ConfiguredGrid(settings)
            self.assertEqual(grid.geometry, GridGeometry(5, 3))
            settings.write_text('{"GRID_WIDTH":')
            clock.return_value = 1
            grid.refresh()
            self.assertEqual(grid.geometry, GridGeometry(5, 3))
            settings.write_text(json.dumps({"GRID_WIDTH": 12, "GRID_HEIGHT": 6}))
            clock.return_value = 2
            grid.refresh()
            self.assertEqual(grid.geometry, GridGeometry(12, 6))


if __name__ == "__main__":
    unittest.main()
