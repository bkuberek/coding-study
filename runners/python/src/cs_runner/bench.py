"""Bench mode (docs/specs/runners.md#bench-mode).

Per size, in request order: each target makes one check call, run like a test case, whose output
is reported for output targets; warmup samples follow until the timings settle; then the timed
repetitions take turns across targets; then each target's memory is measured once. Every call,
or batch of calls, is announced with `bench_start` first, so the CLI can attribute a hang.

A sample makes `calls` back-to-back calls, each on its own freshly decoded input, so calls far
shorter than the timer resolution can still be measured. Decoding, `gc.collect()` and dropping
the results all happen outside the timed region.
"""

import gc
import math
import statistics
import time
import tracemalloc
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from cs_runner.errors import CaseInputError
from cs_runner.events import BenchPoint, EventWriter, Raised, Returned, Sample
from cs_runner.failures import describe
from cs_runner.jobs import ClassTarget, FunctionTarget, PreparedCall, input_error, load_target
from cs_runner.loading import TargetLoadError
from cs_runner.request import BenchInput, BenchJob, BenchSettings, BenchTarget

MEMORY_METRIC = "tracemalloc_peak"
TRACEMALLOC_SLOWDOWN = 10
"""tracemalloc slows allocation-heavy code up to about this much; memory is not measured for
calls whose median time times this exceeds the budget, so the extra call stays within it."""
CV_WINDOW = 5
"""Warmup is settled when the coefficient of variation of the latest runs is low enough."""


def run_bench_jobs(jobs: Sequence[BenchJob], events: EventWriter) -> None:
    for job in jobs:
        events.job_start(job.job_id)
        _Bench(job, events).run(list(_loaded(job, events)))
        events.job_end(job.job_id)


@dataclass(slots=True)
class _Target:
    spec: BenchTarget
    code: FunctionTarget | ClassTarget
    calls: int = 1
    """Calls per sample, grown during warmup until a sample lasts `min_sample_ns`."""
    per_call_ns: list[int] = field(default_factory=list[int])
    """Timed repetitions at the current size."""


def _loaded(job: BenchJob, events: EventWriter) -> Iterator[_Target]:
    for spec in job.targets:
        try:
            yield _Target(spec, load_target(spec.job))
        except TargetLoadError as failure:
            events.target_load_error(job.job_id, spec.target_id, failure.error)


class _Bench:
    def __init__(self, job: BenchJob, events: EventWriter) -> None:
        self._job = job
        self._settings: BenchSettings = job.settings
        self._events = events

    def run(self, targets: list[_Target]) -> None:
        active = targets
        for bench_input in self._job.inputs:
            active = [target for target in active if self._warm_up(target, bench_input)]
            active = self._repetitions(active, bench_input)
            if self._settings.memory:
                active = [target for target in active if self._memory(target, bench_input)]

    def _warm_up(self, target: _Target, bench_input: BenchInput) -> bool:
        """The check call and the warmup samples; False once the target is dropped."""
        point = self._start(target, bench_input)
        try:
            outcome = target.code.run(bench_input.case)
        except CaseInputError as error:
            self._events.bench_error(point, Raised(input_error(error), 0))
            return False
        if not isinstance(outcome, Returned):
            self._events.bench_error(point, outcome)
            return False
        if target.spec.emits_output:
            self._events.bench_output(point, outcome.output)
        if self._over_budget(point, outcome.duration_ns):
            return False
        target.calls = self._batch(bench_input, 1, outcome.duration_ns)
        target.per_call_ns = []
        runs = [outcome.duration_ns]
        warmup_started = time.perf_counter_ns()
        while not self._settled(runs) and not self._warmed_for(warmup_started):
            sample = self._sample(target, bench_input)
            if sample is None or self._over_budget(
                self._point(target, bench_input), sample.per_call_ns
            ):
                return False
            runs.append(sample.per_call_ns)
            target.calls = self._batch(bench_input, target.calls, sample.wall_ns)
        return True

    def _warmed_for(self, started_ns: int) -> bool:
        """Warmup, decoding and collection included, has taken the per-call budget."""
        return time.perf_counter_ns() - started_ns >= self._settings.budget_ns

    def _repetitions(self, active: list[_Target], bench_input: BenchInput) -> list[_Target]:
        remaining = list(active)
        for rep in range(1, self._settings.reps + 1):
            for target in list(remaining):
                sample = self._sample(target, bench_input)
                point = self._point(target, bench_input)
                if sample is None or self._over_budget(point, sample.per_call_ns):
                    remaining.remove(target)
                    continue
                self._events.bench_sample(point, rep, sample)
                target.per_call_ns.append(sample.per_call_ns)
        return remaining

    def _memory(self, target: _Target, bench_input: BenchInput) -> bool:
        """Peak traced memory of one call; False when that call fails."""
        median_ns = statistics.median(target.per_call_ns) if target.per_call_ns else 0
        if median_ns * TRACEMALLOC_SLOWDOWN > self._settings.budget_ns:
            return True
        point = self._start(target, bench_input)
        call = self._prepared(target, bench_input, point)
        if call is None:
            return False
        gc.collect()
        tracemalloc.start()
        try:
            result = call()
        except (Exception, SystemExit) as error:
            tracemalloc.stop()
            self._events.bench_error(point, Raised(describe(error, target.code.path), 0))
            return False
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        del result
        self._events.bench_memory(point, MEMORY_METRIC, peak)
        return True

    def _sample(self, target: _Target, bench_input: BenchInput) -> Sample | None:
        """One timed sample; None (after `bench_error`) when the code fails."""
        point = self._start(target, bench_input)
        prepared: list[PreparedCall] = []
        for _ in range(target.calls):
            call = self._prepared(target, bench_input, point)
            if call is None:
                return None
            prepared.append(call)
        gc.collect()
        results: list[object] = []
        cpu_started = time.process_time_ns()
        started = time.perf_counter_ns()
        try:
            for call in prepared:
                results.append(call())
        except (Exception, SystemExit) as error:
            elapsed = time.perf_counter_ns() - started
            self._events.bench_error(point, Raised(describe(error, target.code.path), elapsed))
            return None
        wall_ns = time.perf_counter_ns() - started
        cpu_ns = time.process_time_ns() - cpu_started
        return Sample(wall_ns, cpu_ns, len(prepared))

    def _prepared(
        self, target: _Target, bench_input: BenchInput, point: BenchPoint
    ) -> PreparedCall | None:
        try:
            return target.code.prepare(bench_input.case)
        except CaseInputError as error:
            self._events.bench_error(point, Raised(input_error(error), 0))
            return None

    def _settled(self, runs: Sequence[int]) -> bool:
        warmup = self._settings.warmup
        if len(runs) >= warmup.max_runs:
            return True
        if len(runs) < warmup.min_runs:
            return False
        latest = runs[-CV_WINDOW:]
        return len(latest) > 1 and _coefficient_of_variation(latest) <= warmup.cv

    def _batch(self, bench_input: BenchInput, calls: int, sample_ns: int) -> int:
        """Calls per sample so that one sample lasts at least `min_sample_ns`."""
        if sample_ns >= self._settings.min_sample_ns:
            return calls
        wanted = math.ceil(calls * self._settings.min_sample_ns / max(sample_ns, 1))
        return max(calls, min(wanted, bench_input.max_batch))

    def _over_budget(self, point: BenchPoint, per_call_ns: int) -> bool:
        if per_call_ns <= self._settings.budget_ns:
            return False
        self._events.bench_budget_exceeded(point, per_call_ns)
        return True

    def _start(self, target: _Target, bench_input: BenchInput) -> BenchPoint:
        point = self._point(target, bench_input)
        self._events.bench_start(point)
        return point

    def _point(self, target: _Target, bench_input: BenchInput) -> BenchPoint:
        return BenchPoint(self._job.job_id, target.spec.target_id, bench_input.size)


def _coefficient_of_variation(values: Sequence[int]) -> float:
    mean = statistics.fmean(values)
    return statistics.pstdev(values) / mean if mean else 0.0
