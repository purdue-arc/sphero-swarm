import json
import os

import pytest

from jsonfile import write_json_atomic


def test_writes_json_with_trailing_newline_and_replaces_the_old_file(tmp_path):
    path = tmp_path / "pis.json"
    path.write_text('{"old": true}\n')

    write_json_atomic(path, {"new": [1, 2]})

    assert json.loads(path.read_text()) == {"new": [1, 2]}
    assert path.read_text().endswith("\n")
    assert [p.name for p in tmp_path.iterdir()] == ["pis.json"]


def test_failed_replace_keeps_the_old_file_and_leaves_no_temp_file(tmp_path, monkeypatch):
    path = tmp_path / "pis.json"
    path.write_text('{"old": true}\n')

    def broken_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", broken_replace)

    with pytest.raises(OSError):
        write_json_atomic(path, {"new": True})

    assert json.loads(path.read_text()) == {"old": True}
    assert [p.name for p in tmp_path.iterdir()] == ["pis.json"]
