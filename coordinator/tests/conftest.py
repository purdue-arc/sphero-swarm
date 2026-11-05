"""Test paths: coordinator/ for the plain imports, the repo root for `controls` and `spherov2`."""
import sys
from pathlib import Path

COORDINATOR_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = COORDINATOR_DIR.parent

for path in (COORDINATOR_DIR, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
