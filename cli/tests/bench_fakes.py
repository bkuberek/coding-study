"""A scripted `RunnerProcess.bench` for use-case and command tests: measurements follow simple
power laws instead of running code."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from coding_study.application.ports import RunnerLaunch
from coding_study.domain.bench_runs import (
    USER_TARGET_ID,
    BenchInput,
    BenchOutput,
    BenchReport,
    BenchRequest,
    BenchSample,
    BenchTarget,
    MemoryMeasurement,
    SizeMeasurements,
    TargetReport,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.runs import RunnerInfo, RunReport, RunRequest, UserError

BENCH_SIZES = (10, 100, 400, 1600)
SAMPLE_CALLS = 1000
"""Enough calls per sample that every size is usable."""

type Measure = Callable[[BenchTarget, BenchInput], SizeMeasurements]


def power_law(
    exponent: float, *, scale: float = 10.0, output: JsonValue = None, memory_exponent: float = 1.0
) -> Measure:
    """`scale * n^exponent` ns per call at every size; output targets report `output`."""
    return timed(lambda size: scale * size**exponent, output, memory_exponent)


def timed(
    per_call_ns: Callable[[int], float], output: JsonValue = None, memory_exponent: float = 1.0
) -> Measure:
    """`per_call_ns(n)` ns per call at every size; output targets report `output`."""

    def measure(target: BenchTarget, bench_input: BenchInput) -> SizeMeasurements:
        per_call = per_call_ns(bench_input.size)
        samples = tuple(
            BenchSample(
                rep, round(per_call * SAMPLE_CALLS), round(per_call * SAMPLE_CALLS), SAMPLE_CALLS
            )
            for rep in range(1, 4)
        )
        memory = MemoryMeasurement(
            "tracemalloc_peak", round(1000 * bench_input.size**memory_exponent)
        )
        reported = BenchOutput(output) if target.emits_output else None
        return SizeMeasurements(bench_input.size, samples, memory, reported)

    return measure


@dataclass
class ScriptedBenchProcess:
    """Measures each target with `measures[target_id]` (default: linear growth)."""

    measures: Mapping[str, Measure] = field(default_factory=dict[str, Measure])
    load_errors: Mapping[str, UserError] = field(default_factory=dict[str, UserError])
    runtime: str = "3.13.2"
    requests: list[BenchRequest] = field(default_factory=list[BenchRequest])

    def run(self, launch: RunnerLaunch, request: RunRequest) -> RunReport:
        raise AssertionError("a bench never runs test cases")

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        self.requests.append(request)
        job = request.job
        return BenchReport(
            RunnerInfo("python", 1, self.runtime),
            tuple(self._target(t, job.inputs) for t in job.targets),
        )

    def _target(self, target: BenchTarget, inputs: tuple[BenchInput, ...]) -> TargetReport:
        error = self.load_errors.get(target.target_id)
        if error is not None:
            return TargetReport(target.target_id, load_error=error)
        measure = self.measures.get(target.target_id, power_law(1.0, output=[0, 1]))
        return TargetReport(target.target_id, tuple(measure(target, i) for i in inputs))


def optimal_user(**overrides: Measure) -> ScriptedBenchProcess:
    """Two-sum with a linear user, a quadratic brute force and a linear hash map."""
    measures: dict[str, Measure] = {
        USER_TARGET_ID: power_law(1.0, scale=11.0, output=[0, 1]),
        "brute-force": power_law(2.0, memory_exponent=0.0),
        "hash-map": power_law(1.0, output=[1, 0]),
    }
    return ScriptedBenchProcess(measures | overrides)
