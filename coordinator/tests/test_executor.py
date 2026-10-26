import time
from types import SimpleNamespace

from controls.Instruction import Instruction
from executor import BatchExecutor


class FakeClient:
    def __init__(self, outcome="complete", ok=True, delay=0.0):
        self.outcome = outcome
        self.ok = ok
        self.delay = delay
        self.commands = []
        self.stops = 0

    def command(self, robot_id, body):
        time.sleep(self.delay)
        self.commands.append((robot_id, body))
        if not self.ok:
            return {"ok": False, "error": "ConnectionError: boom"}
        return {"ok": True, "data": {"robot_id": robot_id, "outcome": self.outcome}}

    def stop_all(self):
        self.stops += 1
        return {"ok": True, "data": {"stopped": []}}


def _resolver(mapping):
    return lambda sphero_id: mapping.get(sphero_id)


def _instr(sphero_id, kind, **fields):
    return {"spheroID": sphero_id, "type": kind, **fields}


def test_instructions_run_in_parallel_and_report_outcome_per_sphero_id():
    clients = {sid: FakeClient(delay=0.3) for sid in (1, 2, 3)}
    executor = BatchExecutor(_resolver({sid: (client, f"SB-{sid}") for sid, client in clients.items()}))
    batch = [_instr(sid, 1, speed=60, duration=1.0) for sid in (1, 2, 3)]

    started = time.monotonic()
    outcomes = executor.run_batch(batch)
    elapsed = time.monotonic() - started

    assert outcomes == {"1": "complete", "2": "complete", "3": "complete"}
    assert elapsed < 0.75  # serial would take about 0.9 s


def test_pi_outcome_is_passed_through_for_cancelled_and_failed():
    cancelled = FakeClient(outcome="cancelled")
    failed = FakeClient(outcome="failed")
    executor = BatchExecutor(_resolver({1: (cancelled, "SB-1"), 2: (failed, "SB-2")}))

    outcomes = executor.run_batch([_instr(1, 3, duration=0.5), _instr(2, 3, duration=0.5)])

    assert outcomes == {"1": "cancelled", "2": "failed"}


def test_unresolvable_sphero_id_is_disconnected_and_sends_nothing():
    executor = BatchExecutor(_resolver({}))

    assert executor.run_batch([_instr(9, 3, duration=0.1)]) == {"9": "disconnected"}


def test_network_failure_is_failed():
    executor = BatchExecutor(_resolver({1: (FakeClient(ok=False), "SB-1")}))

    assert executor.run_batch([_instr(1, 3, duration=0.1)]) == {"1": "failed"}


def test_stop_instruction_calls_stop_all_on_every_distinct_client_and_returns_empty():
    shared = FakeClient()
    other = FakeClient()
    executor = BatchExecutor(_resolver({1: (shared, "SB-1"), 2: (shared, "SB-2"), 3: (other, "SB-3")}))
    batch = [_instr(1, 1, speed=60, duration=1.0), _instr(2, 1, speed=60, duration=1.0), _instr(3, -2)]

    assert executor.run_batch(batch) == {}
    assert shared.stops == 1 and other.stops == 1
    assert shared.commands == [] and other.commands == []


def test_stop_uses_the_clients_callable_when_given():
    client = FakeClient()
    executor = BatchExecutor(_resolver({}), clients=lambda: [client, client])

    executor.run_batch([_instr(1, -1)])

    assert client.stops == 1


def test_led_instruction_object_with_color_attributes_is_translated():
    client = FakeClient()
    executor = BatchExecutor(_resolver({1: (client, "SB-1")}))
    led = SimpleNamespace(spheroID=1, type=0, color=SimpleNamespace(r=255, g=8, b=3))

    executor.run_batch([led])

    assert client.commands == [("SB-1", {"type": 0, "r": 255, "g": 8, "b": 3})]


def test_real_controls_instructions_are_accepted_including_singleton_wrapper_lists():
    client = FakeClient()
    executor = BatchExecutor(_resolver({1: (client, "SB-1"), 2: (client, "SB-2")}))
    batch = [[Instruction(1, 0, 255, 0, 0)], Instruction(2, 2, 90, 0.5)]

    outcomes = executor.run_batch(batch)

    assert outcomes == {"1": "complete", "2": "complete"}
    assert ("SB-1", {"type": 0, "r": 255, "g": 0, "b": 0}) in client.commands
    assert ("SB-2", {"type": 2, "degrees": 90, "duration": 0.5}) in client.commands


def test_empty_batch_returns_empty_outcomes():
    assert BatchExecutor(_resolver({})).run_batch([]) == {}
