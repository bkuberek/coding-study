"""Expanding stress cases into literal per-worker scripts and planning their runs.

Spec: docs/specs/problem-format.md#templates. Run `r` of a case uses seed `seed + r`; each worker
draws from its own `random.Random(f"{seed + r}:{group}:{w}")` stream, in iteration order: in a
`mix`, the choice of step first, then the step's templates left to right. The same seed always
expands to the same scripts (NFR-4).
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass

from coding_study.domain.cases import Case, JsonValue, OperationSequence
from coding_study.domain.concurrency import STALL_GRACE_MS, Concurrency, StressVariant, ThreadKind
from coding_study.domain.problem import Language, Problem
from coding_study.domain.runs import RunCase, StressRun
from coding_study.domain.stress import (
    ArithmeticSequence,
    Literal,
    Pick,
    RandomInteger,
    Step,
    StressScenario,
    Template,
    WorkerGroup,
)

RUN_ID_SEPARATOR = ":"


@dataclass(frozen=True, slots=True)
class WorkerScript:
    group: str
    index: int
    """Within its group."""
    ops: tuple[str, ...]
    args: tuple[tuple[JsonValue, ...], ...]

    @property
    def label(self) -> str:
        """`producer[0]`."""
        return f"{self.group}[{self.index}]"

    @property
    def sequence(self) -> OperationSequence:
        return OperationSequence(self.ops, self.args)


def expand_workers(
    scenario: StressScenario, language: Language, seed: int
) -> tuple[WorkerScript, ...]:
    """Every worker's script for one run with `seed` (already `seed + r`), in ordinal order:
    groups in declaration order, then index within the group."""
    return tuple(
        _expand_worker(group, index, group.repeat.for_language(language), seed)
        for group in scenario.workers
        for index in range(group.count)
    )


def _expand_worker(group: WorkerGroup, index: int, repeat: int, seed: int) -> WorkerScript:
    rng = random.Random(f"{seed}:{group.group}:{index}")
    ops: list[str] = []
    args: list[tuple[JsonValue, ...]] = []
    weights = [step.weight for step in group.steps]
    for iteration in range(repeat):
        steps: Sequence[Step] = (
            rng.choices(group.steps, weights=weights) if group.is_mix else group.steps
        )
        for step in steps:
            ops.append(step.op)
            args.append(tuple(_value(template, index, iteration, rng) for template in step.args))
    return WorkerScript(group.group, index, tuple(ops), tuple(args))


def _value(template: Template, worker: int, iteration: int, rng: random.Random) -> JsonValue:
    match template:
        case Literal(value=value):
            return value
        case ArithmeticSequence(start=start, worker_stride=stride, step=step):
            return start + worker * stride + iteration * step
        case RandomInteger(low=low, high=high):
            return rng.randint(low, high)
        case Pick(values=values):
            return rng.choice(values)


@dataclass(frozen=True, slots=True)
class StressSelection:
    """`cstudy test --stress N --seed S`, or `cstudy verify --stress N`."""

    runs: int | None = None
    """None: `concurrency.runs`."""
    seed: int | None = None
    """None: each case's own seed."""


@dataclass(frozen=True, slots=True)
class PlannedRun:
    """One (stress case, variant, run) as one request case."""

    case: Case
    scenario: StressScenario
    variant: StressVariant
    run: int
    seed: int
    deadline_ms: int
    workers: tuple[WorkerScript, ...]
    request: StressRun

    @property
    def run_id(self) -> str:
        """`s1:platform:0`; runners echo it and never parse it."""
        return RUN_ID_SEPARATOR.join((self.case.id, self.variant.value, str(self.run)))

    def run_case(self) -> RunCase:
        return RunCase(self.run_id, self.request, self.deadline_ms + STALL_GRACE_MS)


def stress_cases(problem: Problem) -> tuple[Case, ...]:
    return tuple(case for case in problem.cases if isinstance(case.input, StressScenario))


def stress_verdict_slots(
    problem: Problem, language: Language
) -> tuple[tuple[Case, StressVariant], ...]:
    """Every (stress case, variant) in `language` in file order then variant order: each one is
    one verdict and one case of the stored tally."""
    concurrency = problem.meta.concurrency
    if concurrency is None:
        return ()
    return tuple(
        (case, variant)
        for case in stress_cases(problem)
        for variant in concurrency.variants(language)
    )


def full_run_case_count(problem: Problem, language: Language) -> int:
    """The `total` a run of every case stores: the sequential cases plus one per (stress case,
    variant), so the JVM's `jvm_threads` variants each count."""
    sequential = len(problem.cases) - len(stress_cases(problem))
    return sequential + len(stress_verdict_slots(problem, language))


def plan_runs(
    problem: Problem, language: Language, selection: StressSelection
) -> tuple[PlannedRun, ...]:
    """Every stress case in file order, then variant, then run index (runners.md#request)."""
    concurrency = problem.meta.concurrency
    if concurrency is None:
        return ()
    runs = selection.runs or concurrency.runs
    return tuple(
        planned
        for case, variant in stress_verdict_slots(problem, language)
        for planned in CaseRuns(case, concurrency, language, variant).plan(
            _seeds(case, selection.seed, runs)
        )
    )


def _seeds(case: Case, base_seed: int | None, runs: int) -> tuple[int, ...]:
    assert isinstance(case.input, StressScenario)
    start = case.input.seed if base_seed is None else base_seed
    return tuple(start + run for run in range(runs))


@dataclass(frozen=True, slots=True)
class CaseRuns:
    """The runs of one stress case in one variant."""

    case: Case
    concurrency: Concurrency
    language: Language
    variant: StressVariant

    @property
    def scenario(self) -> StressScenario:
        scenario = self.case.input
        assert isinstance(scenario, StressScenario)
        return scenario

    def plan(self, seeds: Sequence[int]) -> tuple[PlannedRun, ...]:
        """One run per seed, numbered in order (the conformance suite repeats a seed)."""
        return tuple(self._run(run, seed) for run, seed in enumerate(seeds))

    def _run(self, run: int, seed: int) -> PlannedRun:
        scenario = self.scenario
        deadline_ms = scenario.deadline_ms or self.concurrency.deadline_ms
        workers = expand_workers(scenario, self.language, seed)
        request = StressRun(
            seed=seed,
            deadline_ms=deadline_ms,
            perturb=scenario.perturb.applied_to(self.concurrency.perturb),
            setup=scenario.setup,
            workers=tuple(worker.sequence for worker in workers),
            final=scenario.final.sequence if scenario.final else None,
            thread_kind=self._thread_kind(),
        )
        return PlannedRun(
            self.case, scenario, self.variant, run, seed, deadline_ms, workers, request
        )

    def _thread_kind(self) -> ThreadKind | None:
        if self.variant in (StressVariant.PLATFORM, StressVariant.VIRTUAL):
            return ThreadKind(self.variant.value)
        return None
