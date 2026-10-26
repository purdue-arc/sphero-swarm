import pytest
import requests

from pi_client import (
    ASSIGN_TIMEOUT_SECONDS,
    DRIVE_EXTRA_SECONDS,
    PiClient,
)


class _Response:
    status_code = 200

    def json(self):
        return {"ok": True, "data": {}}


@pytest.fixture
def requested(monkeypatch):
    calls = []

    def fake_request(self, method, url, json=None, headers=None, timeout=None):
        calls.append({"method": method, "url": url, "timeout": timeout})
        return _Response()

    monkeypatch.setattr(requests.Session, "request", fake_request)
    return calls


def test_assign_waits_long_enough_for_a_release_of_moved_balls(requested):
    PiClient("10.0.0.1").assign(["SB-1"])

    assert requested[-1]["url"].endswith("/robots/assign")
    assert requested[-1]["timeout"] == 60 == ASSIGN_TIMEOUT_SECONDS


@pytest.mark.parametrize(("duration_ms", "expected"), [
    (1500, 1.5 + DRIVE_EXTRA_SECONDS),
    (0, DRIVE_EXTRA_SECONDS),
    (30_000, 30 + DRIVE_EXTRA_SECONDS),
])
def test_drive_timeout_is_its_duration_plus_fifteen_seconds(requested, duration_ms, expected):
    PiClient("10.0.0.1").drive("SB-1", 60, 0, duration_ms)

    assert requested[-1]["url"].endswith("/robots/SB-1/drive")
    assert requested[-1]["timeout"] == pytest.approx(expected)
