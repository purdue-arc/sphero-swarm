"""Grid nodes shared by the camera overlay and reported Sphero positions."""

from dataclasses import dataclass
import json
from pathlib import Path
import time


@dataclass(frozen=True)
class GridGeometry:
    width: int = 4
    height: int = 4

    def __post_init__(self):
        if self.width < 2 or self.height < 2:
            raise ValueError("Grid dimensions must contain at least two nodes")

    def pixel_to_grid(self, pixel_x, pixel_y, top_left, bottom_right):
        x0, y0 = top_left
        x1, y1 = bottom_right
        x = (pixel_x - x0) * (self.width - 1) / max(1, x1 - x0)
        y = (pixel_y - y0) * (self.height - 1) / max(1, y1 - y0)
        return (max(0.0, min(x, self.width - 1)),
                max(0.0, min(y, self.height - 1)))

    def lines(self, top_left, bottom_right):
        """Connect nodes, including both diagonals in every complete cell."""
        x0, y0 = top_left
        x1, y1 = bottom_right
        xs = [round(x0 + i * (x1 - x0) / (self.width - 1))
              for i in range(self.width)]
        ys = [round(y0 + j * (y1 - y0) / (self.height - 1))
              for j in range(self.height)]
        segments = [((x, y0), (x, y1)) for x in xs]
        segments.extend(((x0, y), (x1, y)) for y in ys)
        for xa, xb in zip(xs, xs[1:]):
            for ya, yb in zip(ys, ys[1:]):
                segments.extend([((xa, ya), (xb, yb)),
                                 ((xa, yb), (xb, ya))])
        return segments


class ConfiguredGrid:
    """Follow the root settings file, retaining valid geometry during a save."""

    def __init__(self, path):
        self.path = Path(path)
        self.geometry = GridGeometry()
        self._stamp = None
        self._next_check = 0
        self.refresh()

    def refresh(self):
        now = time.monotonic()
        if now < self._next_check:
            return
        self._next_check = now + 0.5
        try:
            stat = self.path.stat()
            stamp = (stat.st_mtime_ns, stat.st_size)
            if stamp == self._stamp:
                return
            values = json.loads(self.path.read_text(encoding="utf-8"))
            geometry = GridGeometry(int(values.get("GRID_WIDTH", 4)),
                                    int(values.get("GRID_HEIGHT", 4)))
        except (OSError, ValueError, TypeError, AttributeError):
            # The GUI may be partway through rewriting the file; try again.
            return
        self.geometry = geometry
        self._stamp = stamp
