"""Runs one controls batch across the Pis and reports a per-ball outcome.

This is the seam gui_driver.py talks to (docs/swarm-control.md, Contract 3).
Instructions arrive in the shape Controls_Server accepts (controls.Instruction
objects, or dicts), get translated into Pi /command bodies, and run in
parallel, one thread per ball, so a batch takes as long as its slowest ball.

Imports nothing from spherov2: Instruction objects are read by duck typing
(attributes and Color.r/.g/.b), so this module loads on any machine.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, Optional

logger = logging.getLogger(__name__)

STOP_TYPES = frozenset({-1, -2})
OUTCOMES = frozenset({"complete", "cancelled", "failed", "disconnected"})

Resolve = Callable[[int], Optional[tuple[Any, str]]]


class BatchExecutor:
    """resolve(sphero_id) -> (PiClient, robot_id) or None when no Pi owns that slot.

    clients() lists the Pis to stop on a stop instruction. If omitted, the
    stop goes to the Pis that own the batch's balls.
    """

    def __init__(self, resolve: Resolve, clients: Optional[Callable[[], Iterable[Any]]] = None):
        self._resolve = resolve
        self._clients = clients

    def run_batch(self, instructions) -> dict[str, str]:
        items = [_unwrap(instruction) for instruction in instructions]
        if any(_field(item, "type") in STOP_TYPES for item in items):
            self._stop_everything(items)
            return {}
        work = [(_field(item, "spheroID"), to_command(item)) for item in items]
        with ThreadPoolExecutor(max_workers=max(1, len(work))) as pool:
            futures = [(str(sphero_id), pool.submit(self._run_one, sphero_id, body))
                       for sphero_id, body in work]
            return {key: future.result() for key, future in futures}

    def _run_one(self, sphero_id: int, body: Optional[dict]) -> str:
        if body is None:
            logger.warning("unsupported instruction for sphero %s", sphero_id)
            return "failed"
        target = self._resolve(sphero_id)
        if target is None:
            return "disconnected"
        client, robot_id = target
        resp = client.command(robot_id, body)
        if not resp.get("ok"):
            logger.warning("command to %s failed: %s", robot_id, resp.get("error"))
            return "failed"
        outcome = (resp.get("data") or {}).get("outcome")
        return outcome if outcome in OUTCOMES else "failed"

    def _stop_everything(self, items: list) -> None:
        if self._clients is not None:
            clients = list(self._clients())
        else:
            clients = self._clients_for([_field(item, "spheroID") for item in items])
        for client in _distinct(clients):
            resp = client.stop_all()
            if not resp.get("ok"):
                logger.warning("stop_all failed: %s", resp.get("error"))

    def _clients_for(self, sphero_ids: list) -> list:
        targets = (self._resolve(sphero_id) for sphero_id in sphero_ids)
        return [target[0] for target in targets if target is not None]


def to_command(instruction: Any) -> Optional[dict]:
    """Translate one instruction into the Pi /command body (Contract 1). None if unsupported."""
    kind = _field(instruction, "type")
    if kind == 0:
        r, g, b = _rgb(instruction)
        return {"type": 0, "r": r, "g": g, "b": b}
    if kind == 1:
        return {"type": 1, "speed": _field(instruction, "speed"), "duration": _field(instruction, "duration")}
    if kind == 2:
        return {"type": 2, "degrees": _field(instruction, "degrees"), "duration": _field(instruction, "duration")}
    if kind == 3:
        return {"type": 3, "duration": _field(instruction, "duration")}
    return None


def _unwrap(instruction: Any) -> Any:
    # Some clients send singleton wrapper lists; Controls_Server unwraps them too.
    while isinstance(instruction, list) and len(instruction) == 1:
        instruction = instruction[0]
    return instruction


def _field(instruction: Any, name: str, default: Any = None) -> Any:
    if isinstance(instruction, dict):
        return instruction.get(name, default)
    return getattr(instruction, name, default)


def _rgb(instruction: Any) -> tuple[int, int, int]:
    if isinstance(instruction, dict):
        return instruction["r"], instruction["g"], instruction["b"]
    color = instruction.color
    return color.r, color.g, color.b


def _distinct(clients: list) -> list:
    return list({id(client): client for client in clients}.values())
