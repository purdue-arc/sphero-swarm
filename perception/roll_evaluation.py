"""Evaluate fixed roll targets using fresh, settled camera measurements."""
import csv
import math
from pathlib import Path


class RollEvaluation:
    def __init__(self, log_path, settle_seconds=0.75, jitter=0.03,
                 tolerance=0.1, timeout=10.0, inches_per_step=12.67):
        self.log_path = Path(log_path)
        self.settle_seconds = settle_seconds
        self.jitter = jitter
        self.tolerance = tolerance
        self.timeout = timeout
        self.inches_per_step = inches_per_step
        if min(settle_seconds, jitter, tolerance, timeout, inches_per_step) <= 0:
            raise ValueError("Evaluation thresholds and scale must be positive")
        self.trials = {}
        self.latest = {}

    def start(self, targets, now):
        for target in targets:
            ident = target["id"]
            previous = self.trials.get(ident)
            if previous and previous["status"] in ("rolling", "settling"):
                self.finish(previous, "superseded")
            measurement = self.latest.get(ident)
            start = measurement[1] if measurement and now - measurement[0] <= 0.5 else None
            self.trials[ident] = dict(target, start=start, status="rolling", samples=[],
                                     deadline=now + target["duration"] + 30,
                                     endpoint=None, error=None, passed=None)

    def complete(self, trial_id, outcomes, now):
        for trial in self.trials.values():
            if trial["trial_id"] != trial_id or trial["status"] != "rolling":
                continue
            if outcomes.get(str(trial["algorithm_id"])) != "complete":
                self.finish(trial, "controls_failed")
            else:
                trial.update(status="settling", completed_at=now,
                             deadline=now + self.timeout, samples=[])

    def update(self, positions, timestamp, now, calibrated=True):
        self.tick(now)
        fresh = calibrated and 0 <= now - timestamp <= 0.5
        if fresh:
            self.latest = {ident: (timestamp, pos) for ident, pos in positions.items()}
        for ident, trial in self.trials.items():
            if trial["status"] not in ("rolling", "settling"):
                continue
            if trial["status"] != "settling":
                continue
            if not fresh or ident not in positions:
                trial["samples"] = []
                continue
            if timestamp <= trial["completed_at"]:
                continue
            samples = trial["samples"]
            if samples and timestamp <= samples[-1][0]:
                continue
            pos = positions[ident]
            if samples and (timestamp - samples[-1][0] > 0.25 or
                            any(math.dist(pos, p) > self.jitter for _, p in samples)):
                samples.clear()
            samples.append((timestamp, pos))
            if len(samples) >= 5 and timestamp - samples[0][0] >= self.settle_seconds:
                trial["endpoint"] = tuple(sum(p[i] for _, p in samples) / len(samples)
                                          for i in (0, 1))
                self.finish(trial, "settled" if trial["start"] else "missing_start")

    def tick(self, now):
        """Expire trials even if the camera stops supplying frames."""
        for trial in self.trials.values():
            if trial["status"] in ("rolling", "settling") and now >= trial["deadline"]:
                self.finish(trial, "timeout")

    def finish(self, trial, status):
        trial["status"] = status
        endpoint, start = trial["endpoint"], trial["start"]
        along = lateral = None
        if endpoint is not None:
            ex, ey = endpoint[0] - trial["x"], endpoint[1] - trial["y"]
            trial["error"] = math.hypot(ex, ey)
            trial["passed"] = trial["error"] <= self.tolerance
            if start:
                dx, dy = trial["x"] - start[0], trial["y"] - start[1]
                length = math.hypot(dx, dy)
                if length:
                    along, lateral = (ex * dx + ey * dy) / length, (-ex * dy + ey * dx) / length
        trial["along_error"], trial["lateral_error"] = along, lateral
        row = {key: trial[key] for key in ("trial_id", "algorithm_id", "id", "speed", "distance", "duration", "status")}
        for name, point in (("start", start), ("target", (trial["x"], trial["y"])), ("final", endpoint)):
            row.update({f"{name}_x": point[0] if point else None,
                        f"{name}_y": point[1] if point else None})
        row.update(error_grid=trial["error"],
                   error_inches=trial["error"] * trial.get("inches_per_step", self.inches_per_step) if trial["error"] is not None else None,
                   along_error_grid=along, lateral_error_grid=lateral,
                   tolerance_grid=self.tolerance, passed=trial["passed"])
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        header = not self.log_path.exists() or self.log_path.stat().st_size == 0
        with self.log_path.open("a", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=list(row))
            if header:
                writer.writeheader()
            writer.writerow(row)

    def snapshot(self):
        return [{k: v for k, v in trial.items() if k != "samples"}
                for trial in self.trials.values()]
