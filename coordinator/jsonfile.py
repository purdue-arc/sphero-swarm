"""Atomic JSON writes for the coordinator's own state files (pis.json, last_assignment.json).

Write to a temp file in the same directory, then os.replace() it over the target.
A crash or power cut mid-write leaves the old file intact instead of a truncated one.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, data: Any) -> None:
    path = Path(path)
    text = json.dumps(data, indent=2) + "\n"
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
