"""Concurrent jobs: sequential cases, then stress runs (docs/specs/runners.md#concurrent-jobs).

Sequential cases run like a design problem's; in the `async` model each runs in its own event
loop and awaitable results are awaited. A project's grading job with stress runs is one too: its
class comes from the project's entry module, and its sequential cases run on its virtual clock
when it has one (docs/specs/runners.md#stress-in-project-jobs). A stress run that leaves worker
threads alive ends the runner with a restart request, so leftover threads never disturb later
runs.
"""

import asyncio
import inspect
import time
from collections.abc import Sequence

from cs_runner.calls import bind
from cs_runner.capture import capture_output
from cs_runner.clock import run_clock_case
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_runner.events import CaseOutcome, EventWriter, InvalidOutput, Raised, Returned
from cs_runner.failures import UserError, describe
from cs_runner.jobs import ClassTarget, arguments_by_name, input_error, member_of
from cs_runner.json_value import Json
from cs_runner.loading import TargetLoadError, find_class, load_entry_class, load_module
from cs_runner.request import ClassJob, ConcurrentJob, Model, OperationCase, ProjectJob, StressCase
from cs_runner.restarts import RestartRequestError
from cs_runner.stress import run_stress

CONSTRUCTOR_INDEX = 0


def run_concurrent_job(job: ConcurrentJob, events: EventWriter) -> None:
    """Raises RestartRequestError after writing `restart_requested`."""
    events.job_start(job.job_id)
    try:
        design = _load(job)
    except TargetLoadError as failure:
        events.load_error(job.job_id, failure.error)
        events.job_end(job.job_id)
        return
    for case in job.cases:
        events.case_start(job.job_id, case.case_id)
        if isinstance(case, StressCase):
            _stress(design, job, case, events)
        elif isinstance(job.design, ProjectJob) and job.design.clock is not None:
            run_clock_case(job.design, design, case, events)
        else:
            events.case_result(job.job_id, case.case_id, _sequential(design, job, case))
    events.job_end(job.job_id)


def _load(job: ConcurrentJob) -> type:
    """The class from its file, or from a project's entry module."""
    match job.design:
        case ClassJob() as design:
            return find_class(load_module(design.path), design)
        case ProjectJob() as project:
            return load_entry_class(project)


def _stress(design: type, job: ConcurrentJob, case: StressCase, events: EventWriter) -> None:
    result = run_stress(design, job, case)
    events.case_result(job.job_id, case.case_id, result.outcome)
    leftovers = result.leftover_threads()
    if leftovers:
        events.restart_requested(f"{leftovers} worker threads still alive after {case.case_id}")
        raise RestartRequestError


def _sequential(design: type, job: ConcurrentJob, case: OperationCase) -> CaseOutcome:
    if job.model is Model.THREADS:
        return ClassTarget(job.design, design).run(case)
    with capture_output() as output:
        outcome = asyncio.run(_AsyncSequence(job, design).run(case))
    return _with_stdout(outcome, output.text())


class _AsyncSequence:
    """One sequential case in the async model: awaitable results are awaited."""

    def __init__(self, job: ConcurrentJob, design: type) -> None:
        self._job = job
        self._design = design
        self._instance: object = None
        self._outputs: list[Json] = []
        self._duration_ns = 0

    async def run(self, case: OperationCase) -> CaseOutcome:
        for index, (op, args) in enumerate(zip(case.ops, case.args, strict=True)):
            failure = await self._operation(index, op, args)
            if failure is not None:
                return failure
        return Returned(self._outputs, self._duration_ns)

    async def _operation(self, index: int, op: str, args: Sequence[Json]) -> CaseOutcome | None:
        try:
            member = member_of(self._job.design, index, op)
            call = bind(member, arguments_by_name(member, args))
        except CaseInputError as error:
            return self._raised(input_error(error), index)
        started = time.perf_counter_ns()
        try:
            value = await self._call(index, member.symbol, call.arguments)
        except (Exception, SystemExit) as error:
            self._duration_ns += time.perf_counter_ns() - started
            return self._raised(describe(error, self._job.user_code), index)
        self._duration_ns += time.perf_counter_ns() - started
        if index == CONSTRUCTOR_INDEX:
            self._instance = value
            self._outputs.append(None)
            return None
        try:
            self._outputs.append(call.encode_result(value))
        except InvalidOutputError as error:
            return InvalidOutput(f"operation {index} ({op}): {error.reason}", self._duration_ns)
        return None

    async def _call(self, index: int, symbol: str, arguments: list[object]) -> object:
        if index == CONSTRUCTOR_INDEX:
            return self._design(*arguments)
        value = getattr(self._instance, symbol)(*arguments)
        return await value if inspect.isawaitable(value) else value

    def _raised(self, error: UserError, index: int) -> Raised:
        return Raised(error, self._duration_ns, op_index=index, partial_output=list(self._outputs))


def _with_stdout(outcome: CaseOutcome, stdout: str) -> CaseOutcome:
    match outcome:
        case Returned():
            return Returned(outcome.output, outcome.duration_ns, stdout)
        case Raised():
            return Raised(
                outcome.error,
                outcome.duration_ns,
                stdout,
                outcome.op_index,
                outcome.partial_output,
            )
        case InvalidOutput():
            return InvalidOutput(outcome.reason, outcome.duration_ns, stdout)
        case _:
            return outcome
