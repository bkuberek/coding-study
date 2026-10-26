"""Scripted answers for the bounded-blocking-queue fixture (tests/fixtures/concurrency)."""

from collections import deque

from coding_study.domain.cases import JsonValue, OperationSequence
from coding_study.domain.runs import (
    CaseOutcome,
    Returned,
    RunCase,
    RunJob,
    Stalled,
    StressCompleted,
    StressRun,
    WorkerProgress,
)


def queue(job: RunJob, case: RunCase) -> CaseOutcome:
    """A correct queue: sequential cases replay on a deque; stress takes hand over every put."""
    if isinstance(case.input, StressRun):
        return _stress(case.input)
    assert isinstance(case.input, OperationSequence)
    items: deque[JsonValue] = deque()
    outputs: list[JsonValue] = []
    for op, args in zip(case.input.ops, case.input.args, strict=True):
        if op == "put":
            items.append(args[0])
        outputs.append(items.popleft() if op == "take" else len(items) if op == "size" else None)
    return Returned(outputs, 1000)


def _stress(run: StressRun) -> StressCompleted:
    values = deque(
        args[0]
        for worker in run.workers
        for op, args in zip(worker.ops, worker.args, strict=True)
        if op == "put"
    )
    workers = tuple(
        tuple(
            values.popleft() if op == "take" else 0 if op == "size" else None for op in worker.ops
        )
        for worker in run.workers
    )
    return StressCompleted((None,), workers, (0,), {}, 2_000_000)


def duplicating(job: RunJob, case: RunCase) -> CaseOutcome:
    """Every stress run hands the first value to two consumers."""
    outcome = queue(job, case)
    if not isinstance(outcome, StressCompleted) or not isinstance(case.input, StressRun):
        return outcome
    takers = [index for index, worker in enumerate(case.input.workers) if "take" in worker.ops]
    first, second = outcome.workers[takers[0]], outcome.workers[takers[1]]
    workers = list(outcome.workers)
    workers[takers[1]] = (first[0], *second[1:])
    return StressCompleted(outcome.setup, tuple(workers), outcome.final, outcome.sections, 1)


def stalling(job: RunJob, case: RunCase) -> CaseOutcome:
    """Every stress run stalls with the first producer inside its first put."""
    if not isinstance(case.input, StressRun):
        return queue(job, case)
    return Stalled((WorkerProgress(0, 0, True),), 5_000_000_000)
