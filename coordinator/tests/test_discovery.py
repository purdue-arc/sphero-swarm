import json

import pytest

import discovery
from discovery import PiInfo, discover, normalise_mac, save_last_ips

HEALTH = {
    "status": "alive",
    "hostname": "sphero-pi-01",
    "macs": {"wlan0": "AA-BB-CC-DD-EE-01", "eth0": "11:22:33:44:55:66"},
    "version": {"branch": "main", "commit": "abc123"},
    "state": "idle",
    "connected_count": 2,
}


def _config(*pis, sweep=False):
    return {"port": 5000, "token": "change-me", "subnet_sweep": sweep, "pis": list(pis)}


def _probe_only(answers):
    """Probe that answers from a dict of ip -> health and records every call."""
    calls = []

    def probe(ip):
        calls.append(ip)
        return answers.get(ip)

    probe.calls = calls
    return probe


def test_placeholder_mac_is_matched_by_last_ip_alone():
    config = _config({"number": 1, "mac": "XX:XX:XX:XX:XX:XX", "last_ip": "10.0.0.5"})

    found = discover(config, sweep=False, probe=_probe_only({"10.0.0.5": HEALTH}))

    assert found[0].online is True
    assert found[0].ip == "10.0.0.5"
    assert found[0].hostname == "sphero-pi-01"
    assert found[0].connected_count == 2


def test_placeholder_mac_with_no_answer_is_offline_and_keeps_last_ip():
    config = _config({"number": 1, "mac": "XX:XX:XX:XX:XX:XX", "last_ip": "10.0.0.5"})

    found = discover(config, sweep=False, probe=_probe_only({}))

    assert found == [PiInfo(number=1, mac="XX:XX:XX:XX:XX:XX", ip="10.0.0.5", online=False)]


def test_real_mac_matches_last_ip_case_and_separator_insensitively():
    config = _config({"number": 1, "mac": "aa:bb:cc:dd:ee:01", "last_ip": "10.0.0.5"})

    found = discover(config, sweep=False, probe=_probe_only({"10.0.0.5": HEALTH}))

    assert found[0].online is True


def test_real_mac_that_does_not_match_the_reported_macs_is_not_online():
    config = _config({"number": 1, "mac": "de:ad:be:ef:00:00", "last_ip": "10.0.0.5"})

    found = discover(config, sweep=False, probe=_probe_only({"10.0.0.5": HEALTH}))

    assert found[0].online is False


def test_real_mac_not_at_last_ip_is_found_by_sweeping_the_subnet(monkeypatch):
    monkeypatch.setattr(discovery, "local_ip", lambda *_: "10.0.5.9")
    config = _config({"number": 1, "mac": "AA:BB:CC:DD:EE:01", "last_ip": None})
    probe = _probe_only({"10.0.5.42": HEALTH})

    found = discover(config, sweep=True, probe=probe)

    assert found[0].online is True
    assert found[0].ip == "10.0.5.42"
    assert "10.0.5.9" not in probe.calls


def test_sweep_does_not_run_when_disabled(monkeypatch):
    monkeypatch.setattr(discovery, "local_ip", lambda *_: "10.0.5.9")
    config = _config({"number": 1, "mac": "AA:BB:CC:DD:EE:01", "last_ip": None})
    probe = _probe_only({"10.0.5.42": HEALTH})

    found = discover(config, sweep=False, probe=probe)

    assert found[0].online is False
    assert probe.calls == []


def test_sweep_skips_ips_already_found_by_last_ip(monkeypatch):
    monkeypatch.setattr(discovery, "local_ip", lambda *_: "10.0.5.9")
    config = _config(
        {"number": 1, "mac": "AA:BB:CC:DD:EE:01", "last_ip": "10.0.5.20"},
        {"number": 2, "mac": "11:22:33:44:55:66", "last_ip": None},
    )
    other = dict(HEALTH, macs={"wlan0": "11:22:33:44:55:66"})
    probe = _probe_only({"10.0.5.20": HEALTH, "10.0.5.77": other})

    found = discover(config, sweep=True, probe=probe)

    assert [info.ip for info in found] == ["10.0.5.20", "10.0.5.77"]
    assert probe.calls.count("10.0.5.20") == 1


def test_normalise_mac_handles_dashes_and_case():
    assert normalise_mac("AA-bb-CC:dd-EE:01") == "aa:bb:cc:dd:ee:01"


def test_save_last_ips_returns_new_config_without_mutating_input(tmp_path):
    path = tmp_path / "pis.json"
    config = _config({"number": 1, "mac": "AA:BB:CC:DD:EE:01", "last_ip": None},
                     {"number": 2, "mac": "XX:XX:XX:XX:XX:XX", "last_ip": "10.0.0.2"})
    found = [PiInfo(number=1, mac="AA:BB:CC:DD:EE:01", ip="10.0.5.42", online=True)]
    snapshot = json.loads(json.dumps(config))

    new_config = save_last_ips(path, config, found)

    assert config == snapshot
    assert new_config["pis"][0]["last_ip"] == "10.0.5.42"
    assert new_config["pis"][1]["last_ip"] == "10.0.0.2"
    assert json.loads(path.read_text()) == new_config


def test_save_last_ips_does_not_write_when_nothing_changed(tmp_path):
    path = tmp_path / "pis.json"
    config = _config({"number": 1, "mac": "AA:BB:CC:DD:EE:01", "last_ip": "10.0.5.42"})
    found = [PiInfo(number=1, mac="AA:BB:CC:DD:EE:01", ip="10.0.5.42", online=True)]

    save_last_ips(path, config, found)

    assert not path.exists()


class _FakeUdpSocket:
    """Stands in for socket.socket(AF_INET, SOCK_DGRAM). connect() fails for unroutable targets."""

    routable: dict = {}
    attempts: list = []

    def __init__(self, *args, **kwargs):
        self._target = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def connect(self, address):
        self._target = address[0]
        self.attempts.append(address[0])
        if self._target not in self.routable:
            raise OSError("network is unreachable")

    def getsockname(self):
        return (self.routable[self._target], 0)


@pytest.fixture
def fake_udp(monkeypatch):
    _FakeUdpSocket.attempts = []
    monkeypatch.setattr(discovery.socket, "socket", _FakeUdpSocket)
    return _FakeUdpSocket


def test_local_ip_tries_known_pi_addresses_before_the_internet_fallback(fake_udp):
    fake_udp.routable = {"192.168.11.135": "192.168.11.50", "8.8.8.8": "203.0.113.9"}

    assert discovery.local_ip(["192.168.11.135"]) == "192.168.11.50"
    assert fake_udp.attempts == ["192.168.11.135"]


def test_local_ip_falls_back_to_8_8_8_8_when_no_known_pi_routes(fake_udp):
    fake_udp.routable = {"8.8.8.8": "203.0.113.9"}

    assert discovery.local_ip(["10.99.0.7"]) == "203.0.113.9"
    assert fake_udp.attempts == ["10.99.0.7", "8.8.8.8"]


def test_local_ip_is_none_on_an_isolated_lan_with_no_route(fake_udp):
    fake_udp.routable = {}

    assert discovery.local_ip(["192.168.11.135"]) is None


def test_skipped_sweep_is_logged_with_the_reason(monkeypatch, caplog):
    monkeypatch.setattr(discovery, "local_ip", lambda *_: None)
    config = _config({"number": 1, "mac": "AA:BB:CC:DD:EE:01", "last_ip": "192.168.11.135"},
                     {"number": 2, "mac": "AA:BB:CC:DD:EE:02", "last_ip": None})

    with caplog.at_level("WARNING", logger="discovery"):
        found = discover(config, sweep=True, probe=_probe_only({}))

    assert all(not info.online for info in found)
    assert "subnet sweep skipped" in caplog.text
    assert "192.168.11.135" in caplog.text


def test_save_last_ips_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "pis.json"
    config = _config({"number": 1, "mac": "AA:BB:CC:DD:EE:01", "last_ip": None})
    found = [PiInfo(number=1, mac="AA:BB:CC:DD:EE:01", ip="10.0.5.42", online=True)]

    save_last_ips(path, config, found)

    assert [p.name for p in tmp_path.iterdir()] == ["pis.json"]
