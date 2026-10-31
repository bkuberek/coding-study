"""The JSON Lines event stream written to `--out` (docs/specs/runners.md#event-stream).

Every event is flushed as soon as it is written so the CLI can follow progress and attribute a
hang or crash to the case in progress.
"""

import json
import platform
from dataclasses import dataclass, field
from typing import TextIO

from cs_runner.failures import UserError
from cs_runner.json_value import Json
from cs_runner.request import PROTOCOL_VERSION

RUNNER_NAME = "python"
FEATURES = ["stress", "project", "suite"]
"""Protocol additions this runner implements (docs/specs/runners.md#capability and
#project-jobs)."""


@dataclass(frozen=True, slots=True)
class Returned:
    """`ok`; class kinds hold one output per operation."""

    output: Json
    duration_ns: int
    stdout: str = ""

    def fields(self) -> dict[str, Json]:
        return {"status": "ok", "output": self.output, **_measured(self.duration_ns, self.stdout)}


@dataclass(frozen=True, slots=True)
class Raised:
    """`error`; class kinds name the failing operation and the outputs before it."""

    error: UserError
    duration_ns: int
    stdout: str = ""
    op_index: int | None = None
    partial_output: list[Json] = field(default_factory=list[Json])

    def fields(self) -> dict[str, Json]:
        fields: dict[str, Json] = {"status": "error", "error": self.error.to_json()}
        if self.op_index is not None:
            fields |= {"op_index": self.op_index, "partial_output": self.partial_output}
        return fields | _measured(self.duration_ns, self.stdout)


@dataclass(frozen=True, slots=True)
class InvalidOutput:
    reason: str
    duration_ns: int
    stdout: str = ""

    def fields(self) -> dict[str, Json]:
        return {
            "status": "invalid_output",
            "reason": self.reason,
            **_measured(self.duration_ns, self.stdout),
        }


@dataclass(frozen=True, slots=True)
class WorkerProgress:
    worker: int
    completed: int
    in_op: bool

    def to_json(self) -> dict[str, Json]:
        return {"worker": self.worker, "completed": self.completed, "in_op": self.in_op}


@dataclass(frozen=True, slots=True)
class FailedAt:
    """Where a stress run failed: phase `setup`, `worker` or `final`, and the op index."""

    phase: str
    op_index: int
    worker: int | None = None
    progress: tuple[WorkerProgress, ...] = ()

    def fields(self) -> dict[str, Json]:
        fields: dict[str, Json] = {"phase": self.phase, "op_index": self.op_index}
        if self.worker is not None:
            fields |= {"worker": self.worker, "progress": _progress(self.progress)}
        return fields


@dataclass(frozen=True, slots=True)
class StressFailed:
    """`error` or `invalid_output` of a stress run."""

    failure: "Raised | InvalidOutput"
    at: FailedAt

    @property
    def stdout(self) -> str:
        return self.failure.stdout

    def fields(self) -> dict[str, Json]:
        return self.failure.fields() | self.at.fields()


@dataclass(frozen=True, slots=True)
class Section:
    entries: int
    violations: int
    max_occupancy: int


@dataclass(frozen=True, slots=True)
class StressReturned:
    """`ok` of a stress run: one output per op of setup, every worker script and final."""

    setup: list[Json]
    workers: list[list[Json]]
    final: list[Json]
    sections: dict[str, Section]
    duration_ns: int
    stdout: str = ""

    def fields(self) -> dict[str, Json]:
        output: dict[str, Json] = {
            "setup": self.setup,
            "workers": list[Json](self.workers),
            "final": self.final,
        }
        sections: dict[str, Json] = {
            name: {
                "entries": section.entries,
                "violations": section.violations,
                "max_occupancy": section.max_occupancy,
            }
            for name, section in self.sections.items()
        }
        fields: dict[str, Json] = {"status": "ok", "output": output, "sections": sections}
        return fields | _measured(self.duration_ns, self.stdout)


@dataclass(frozen=True, slots=True)
class Stalled:
    """Workers were still unfinished at the run's deadline."""

    progress: tuple[WorkerProgress, ...]
    duration_ns: int
    stdout: str = ""

    def fields(self) -> dict[str, Json]:
        fields: dict[str, Json] = {"status": "stalled", "progress": _progress(self.progress)}
        return fields | _measured(self.duration_ns, self.stdout)


@dataclass(frozen=True, slots=True)
class Passed:
    """`ok` of a suite job's test, which has no output (docs/specs/runners.md#suite-job)."""

    duration_ns: int
    stdout: str = ""

    def fields(self) -> dict[str, Json]:
        return {"status": "ok", **_measured(self.duration_ns, self.stdout)}


@dataclass(frozen=True, slots=True)
class AssertionFailed:
    """`failed`: a suite job's test whose assertion failed, with the framework's text."""

    message: str
    duration_ns: int
    stdout: str = ""

    def fields(self) -> dict[str, Json]:
        fields: dict[str, Json] = {"status": "failed", "message": self.message}
        return fields | _measured(self.duration_ns, self.stdout)


@dataclass(frozen=True, slots=True)
class Skipped:
    """`skipped`: the framework skipped a suite job's test, for the reason in `message`."""

    message: str
    duration_ns: int
    stdout: str = ""

    def fields(self) -> dict[str, Json]:
        fields: dict[str, Json] = {"status": "skipped", "message": self.message}
        return fields | _measured(self.duration_ns, self.stdout)


type SequentialOutcome = Returned | Raised | InvalidOutput
"""What one call sequence produced: a function or design case, or a bench check call."""
type SuiteOutcome = Passed | AssertionFailed | Raised | Skipped
"""What one test of a suite job came to."""
type CaseOutcome = SequentialOutcome | StressReturned | StressFailed | Stalled | SuiteOutcome


@dataclass(frozen=True, slots=True)
class BenchPoint:
    """One target at one input size of a bench job; every bench event names one."""

    job_id: str
    target_id: str
    size: int

    def fields(self, event: str) -> dict[str, Json]:
        return {
            "event": event,
            "job_id": self.job_id,
            "target_id": self.target_id,
            "size": self.size,
        }


@dataclass(frozen=True, slots=True)
class Sample:
    """`calls` back-to-back calls, each on a fresh input."""

    wall_ns: int
    cpu_ns: int
    calls: int

    @property
    def per_call_ns(self) -> int:
        return self.wall_ns // self.calls


class EventWriter:
    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def hello(self) -> None:
        self._emit(
            {
                "event": "hello",
                "runner": RUNNER_NAME,
                "protocol": PROTOCOL_VERSION,
                "runtime": platform.python_version(),
                "features": list[Json](FEATURES),
            }
        )

    def job_start(self, job_id: str) -> None:
        self._emit({"event": "job_start", "job_id": job_id})

    def case_start(self, job_id: str, case_id: str) -> None:
        self._emit({"event": "case_start", "job_id": job_id, "case_id": case_id})

    def case_result(self, job_id: str, case_id: str, outcome: CaseOutcome) -> None:
        event: dict[str, Json] = {"event": "case_result", "job_id": job_id, "case_id": case_id}
        self._emit(event | outcome.fields())

    def load_error(self, job_id: str, error: UserError) -> None:
        self._emit({"event": "load_error", "job_id": job_id, "error": error.to_json()})

    def job_end(self, job_id: str) -> None:
        self._emit({"event": "job_end", "job_id": job_id})

    def target_load_error(self, job_id: str, target_id: str, error: UserError) -> None:
        """Bench mode: one target did not load; the job's other targets still run."""
        event: dict[str, Json] = {
            "event": "load_error",
            "job_id": job_id,
            "target_id": target_id,
            "error": error.to_json(),
        }
        self._emit(event)

    def bench_start(self, point: BenchPoint) -> None:
        self._emit(point.fields("bench_start"))

    def bench_output(self, point: BenchPoint, output: Json) -> None:
        self._emit(point.fields("bench_output") | {"output": output})

    def bench_error(self, point: BenchPoint, outcome: Raised | InvalidOutput) -> None:
        self._emit(point.fields("bench_error") | outcome.fields())

    def bench_sample(self, point: BenchPoint, rep: int, sample: Sample) -> None:
        measured: dict[str, Json] = {
            "rep": rep,
            "wall_ns": sample.wall_ns,
            "cpu_ns": sample.cpu_ns,
            "calls": sample.calls,
        }
        self._emit(point.fields("bench_sample") | measured)

    def bench_memory(self, point: BenchPoint, metric: str, allocated_bytes: int) -> None:
        self._emit(point.fields("bench_memory") | {"metric": metric, "bytes": allocated_bytes})

    def bench_budget_exceeded(self, point: BenchPoint, wall_ns: int) -> None:
        self._emit(point.fields("bench_budget_exceeded") | {"wall_ns": wall_ns})

    def restart_requested(self, reason: str) -> None:
        """After a stress run's result, when its worker threads are still alive."""
        self._emit({"event": "restart_requested", "reason": reason})

    def bye(self) -> None:
        self._emit({"event": "bye"})

    def _emit(self, event: dict[str, Json]) -> None:
        self._stream.write(json.dumps(event, allow_nan=False) + "\n")
        self._stream.flush()


def _progress(progress: tuple[WorkerProgress, ...]) -> list[Json]:
    return [item.to_json() for item in progress]


def _measured(duration_ns: int, stdout: str) -> dict[str, Json]:
    """Every result carries its duration; empty output is omitted."""
    fields: dict[str, Json] = {"duration_ns": duration_ns}
    if stdout:
        fields["stdout"] = stdout
    return fields
