"""Finds which Pis are online and at what IP, for the dashboard's Pi cards.

Two passes, cheapest first. Probe each Pi's last known IP. For Pis with a
real MAC that did not answer, sweep the mini-PC's /24 for /health and match
the MAC the Pi reports. Pis with a placeholder MAC (contains X, i.e. not
filled in yet) can only be matched by last_ip: a sweep has no real MAC to
compare against.

The probe is injectable so tests never touch the network.
"""
import ipaddress
import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from jsonfile import write_json_atomic
from pi_client import PiClient

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_SECONDS = 0.5
SWEEP_WORKERS = 64
DEFAULT_PORT = 5000
FALLBACK_ROUTE_TARGET = "8.8.8.8"

Probe = Callable[[str], Optional[dict]]


@dataclass(frozen=True)
class PiInfo:
    number: int
    mac: str
    ip: Optional[str]
    online: bool
    hostname: Optional[str] = None
    state: Optional[str] = None
    version: Optional[dict] = None
    connected_count: int = 0


def normalise_mac(mac: str) -> str:
    return mac.replace("-", ":").strip().lower()


def is_placeholder_mac(mac: str) -> bool:
    return "x" in mac.lower()


def local_ip(targets: Iterable[str] = ()) -> Optional[str]:
    """Outbound interface IP for the first target that routes.

    A UDP connect() sends nothing; it only asks the OS which interface would be
    used. The known Pi addresses come first because they sit on the lab subnet,
    which is the only route that exists on an isolated LAN with no gateway.
    8.8.8.8 is the last resort for machines that do have internet access.
    """
    for target in [*targets, FALLBACK_ROUTE_TARGET]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((target, 80))
                ip = sock.getsockname()[0]
        except OSError:
            continue
        if not ip.startswith("127.") and ip != "0.0.0.0":
            return ip
    return None


def make_probe(port: int, timeout: float = PROBE_TIMEOUT_SECONDS) -> Probe:
    def probe(ip: str) -> Optional[dict]:
        resp = PiClient(ip, port, timeout=timeout).health()
        return resp.get("data") if resp.get("ok") else None
    return probe


def discover(config: dict, sweep: bool, probe: Optional[Probe] = None) -> list[PiInfo]:
    probe = probe or make_probe(config.get("port", DEFAULT_PORT))
    pis = config["pis"]
    hits = _probe_last_ips(pis, probe)
    if sweep and any(_needs_sweep(pi, hits) for pi in pis):
        hits.update(_sweep_hits(pis, hits, probe))
    return [_info(pi, hits.get(pi["number"])) for pi in pis]


def save_last_ips(path, config: dict, found: Iterable[PiInfo]) -> dict:
    """Return a new config with last_ip updated for every Pi found online.

    Writes the file only when something changed, so a clean discovery does
    not churn pis.json. The input config is not mutated.
    """
    ips = {info.number: info.ip for info in found if info.online and info.ip}
    new_pis = [
        {**pi, "last_ip": ips[pi["number"]]} if pi["number"] in ips else dict(pi)
        for pi in config["pis"]
    ]
    new_config = {**config, "pis": new_pis}
    if new_config != config:
        write_json_atomic(Path(path), new_config)
    return new_config


def _macs_of(health: dict) -> set[str]:
    return {normalise_mac(mac) for mac in (health.get("macs") or {}).values()}


def _matches(pi: dict, health: dict) -> bool:
    if is_placeholder_mac(pi["mac"]):
        return True
    return normalise_mac(pi["mac"]) in _macs_of(health)


def _needs_sweep(pi: dict, hits: dict) -> bool:
    return pi["number"] not in hits and not is_placeholder_mac(pi["mac"])


def _probe_last_ips(pis: list[dict], probe: Probe) -> dict[int, tuple[str, dict]]:
    hits = {}
    for pi in pis:
        ip = pi.get("last_ip")
        if not ip:
            continue
        health = probe(ip)
        if health and _matches(pi, health):
            hits[pi["number"]] = (ip, health)
    return hits


def _sweep_hits(pis: list[dict], hits: dict, probe: Probe) -> dict[int, tuple[str, dict]]:
    known_ips = [pi["last_ip"] for pi in pis if pi.get("last_ip")]
    local = local_ip(known_ips)
    if local is None:
        logger.warning("subnet sweep skipped: no outbound interface found (tried last_ip of %s, then %s); "
                       "Pis without an answer at last_ip stay offline",
                       known_ips or "no known IPs", FALLBACK_ROUTE_TARGET)
        return {}
    found_ips = {ip for ip, _ in hits.values()}
    network = ipaddress.ip_network(f"{local}/24", strict=False)
    candidates = [str(host) for host in network.hosts()
                  if str(host) not in found_ips and str(host) != local]
    with ThreadPoolExecutor(max_workers=SWEEP_WORKERS) as pool:
        healths = list(pool.map(probe, candidates))
    answered = {ip: health for ip, health in zip(candidates, healths) if health}
    new_hits = {}
    for pi in pis:
        if not _needs_sweep(pi, hits):
            continue
        match = next(((ip, health) for ip, health in answered.items()
                      if normalise_mac(pi["mac"]) in _macs_of(health)), None)
        if match:
            new_hits[pi["number"]] = match
    return new_hits


def _info(pi: dict, hit: Optional[tuple[str, dict]]) -> PiInfo:
    if hit is None:
        return PiInfo(number=pi["number"], mac=pi["mac"], ip=pi.get("last_ip"), online=False)
    ip, health = hit
    return PiInfo(
        number=pi["number"],
        mac=pi["mac"],
        ip=ip,
        online=True,
        hostname=health.get("hostname"),
        state=health.get("state"),
        version=health.get("version"),
        connected_count=int(health.get("connected_count") or 0),
    )
