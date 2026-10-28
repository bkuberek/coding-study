"""Runs the cases of each job and reports them as events (docs/specs/runners.md).

Inputs are decoded fresh for every case, and every case starts with a fresh `decimal` context, so
code that changes the precision or rounding cannot affect a later case. `duration_ns` covers only
the calls into user code: decoding inputs and encoding outputs are outside the timed region.
"""

import time
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from decimal import Context, localcontext
from functools import partial

from cs_runner.calls import bind
from cs_runner.capture import capture_output
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_runner.events import EventWriter, InvalidOutput, Raised, Returned, SequentialOutcome
from cs_runner.failures import UserError, describe
from cs_runner.json_value import Json
from cs_runner.loading import TargetLoadError, find_class, find_function, load_module
from cs_runner.request import (
    BenchCase,
    ClassJob,
    FunctionCase,
    FunctionJob,
    Member,
    OperationCase,
    SequentialJob,
)

CONSTRUCTOR_INDEX = 0

type CaseRun = Callable[[], SequentialOutcome]
type PreparedCall = Callable[[], object]
"""A call into user code with its inputs already decoded; returns what the code returned."""


def run_jobs(jobs: Sequence[SequentialJob], events: EventWriter) -> None:
    for job in jobs:
        run_job(job, events)


def run_job(job: SequentialJob, events: EventWriter) -> None:
    events.job_start(job.job_id)
    try:
        cases = _loaded_cases(job)
    except TargetLoadError as failure:
        events.load_error(job.job_id, failure.error)
    else:
        for case_id, run_case in cases:
            events.case_start(job.job_id, case_id)
            events.case_result(job.job_id, case_id, run_case())
    events.job_end(job.job_id)


def load_target(job: SequentialJob) -> "FunctionTarget | ClassTarget":
    """Raises TargetLoadError when the file, the symbol or its signature does not fit."""
    module = load_module(job.path)
    match job:
        case FunctionJob():
            return FunctionTarget(job, find_function(module, job.function))
        case ClassJob():
            return ClassTarget(job, find_class(module, job))


def _loaded_cases(job: SequentialJob) -> list[tuple[str, CaseRun]]:
    target = load_target(job)
    return [(case.case_id, partial(target.run, case)) for case in job.cases]


@dataclass(frozen=True, slots=True)
class _TimedCall:
    value: object
    error: BaseException | None
    duration_ns: int


def _call(target: Callable[..., object], arguments: Sequence[object]) -> _TimedCall:
    """Calls user code; `SystemExit` is a case error like any exception."""
    started = time.perf_counter_ns()
    try:
        value = target(*arguments)
    except (Exception, SystemExit) as error:
        return _TimedCall(None, error, time.perf_counter_ns() - started)
    return _TimedCall(value, None, time.perf_counter_ns() - started)


def _fresh_decimal_context() -> AbstractContextManager[Context]:
    """The current thread's decimal context becomes a default one until the block ends."""
    return localcontext(Context())


def input_error(error: CaseInputError) -> UserError:
    return UserError(type(error).__name__, str(error))


class FunctionTarget:
    def __init__(self, job: FunctionJob, function: Callable[..., object]) -> None:
        self._job = job
        self._function = function

    @property
    def path(self) -> str:
        return self._job.path

    def run(self, case: BenchCase) -> SequentialOutcome:
        """One case as `cstudy test` runs it; raises CaseInputError for an operation sequence."""
        return self._run(_function_case(case))

    def prepare(self, case: BenchCase) -> PreparedCall:
        """Decodes fresh arguments; raises CaseInputError when the input does not fit."""
        call = bind(self._job.function, _function_case(case).values)
        return partial(self._function, *call.arguments)

    def _run(self, case: FunctionCase) -> SequentialOutcome:
        try:
            call = bind(self._job.function, case.values)
        except CaseInputError as error:
            return Raised(input_error(error), duration_ns=0)
        with _fresh_decimal_context(), capture_output() as output:
            timed = _call(self._function, call.arguments)
        stdout = output.text()
        if timed.error is not None:
            return Raised(describe(timed.error, self._job.path), timed.duration_ns, stdout)
        try:
            return Returned(call.encode_result(timed.value), timed.duration_ns, stdout)
        except InvalidOutputError as error:
            return InvalidOutput(error.reason, timed.duration_ns, stdout)


class ClassTarget:
    def __init__(self, job: ClassJob, design: type) -> None:
        self._job = job
        self._design = design

    @property
    def path(self) -> str:
        return self._job.path

    def run(self, case: BenchCase) -> SequentialOutcome:
        """One case as `cstudy test` runs it; raises CaseInputError for function arguments."""
        with _fresh_decimal_context(), capture_output() as output:
            outcome = _OperationSequence(self._job, self._design).run(_operation_case(case))
        return replace(outcome, stdout=output.text())

    def prepare(self, case: BenchCase) -> PreparedCall:
        """The whole sequence as one call: construct, then call each method on the instance."""
        sequence = _operation_case(case)
        members = [member_of(self._job, index, op) for index, op in enumerate(sequence.ops)]
        arguments = [
            bind(member, arguments_by_name(member, args)).arguments
            for member, args in zip(members, sequence.args, strict=True)
        ]
        symbols = [member.symbol for member in members[1:]]
        return partial(_run_operations, self._design, symbols, arguments)


def _run_operations(
    design: type, symbols: Sequence[str], arguments: Sequence[list[object]]
) -> list[object]:
    instance = design(*arguments[CONSTRUCTOR_INDEX])
    results: list[object] = [instance]
    for symbol, method_arguments in zip(symbols, arguments[1:], strict=True):
        results.append(getattr(instance, symbol)(*method_arguments))
    return results


def _function_case(case: BenchCase) -> FunctionCase:
    if not isinstance(case, FunctionCase):
        raise CaseInputError("a function job takes arguments, not an operation sequence")
    return case


def _operation_case(case: BenchCase) -> OperationCase:
    if not isinstance(case, OperationCase):
        raise CaseInputError("a class job takes an operation sequence, not arguments")
    return case


class _OperationSequence:
    """One case of a class kind: the constructor, then each operation on the new instance."""

    def __init__(self, job: ClassJob, design: type) -> None:
        self._job = job
        self._design = design
        self._instance: object = None
        self._outputs: list[Json] = []
        self._duration_ns = 0

    def run(self, case: OperationCase) -> SequentialOutcome:
        for index, (op, args) in enumerate(zip(case.ops, case.args, strict=True)):
            failure = self._operation(index, op, args)
            if failure is not None:
                return failure
        return Returned(self._outputs, self._duration_ns)

    def _operation(self, index: int, op: str, args: Sequence[Json]) -> SequentialOutcome | None:
        """Runs one operation; returns the case outcome when it ends the case."""
        try:
            member = member_of(self._job, index, op)
            call = bind(member, arguments_by_name(member, args))
        except CaseInputError as error:
            return self._raised(input_error(error), index)
        timed = _call(self._callable(index, member), call.arguments)
        self._duration_ns += timed.duration_ns
        if timed.error is not None:
            return self._raised(describe(timed.error, self._job.path), index)
        if index == CONSTRUCTOR_INDEX:
            self._instance = timed.value
            self._outputs.append(None)
            return None
        try:
            self._outputs.append(call.encode_result(timed.value))
        except InvalidOutputError as error:
            return InvalidOutput(f"operation {index} ({op}): {error.reason}", self._duration_ns)
        return None

    def _callable(self, index: int, member: Member) -> Callable[..., object]:
        if index == CONSTRUCTOR_INDEX:
            return self._design
        return getattr(self._instance, member.symbol)

    def _raised(self, error: UserError, index: int) -> Raised:
        return Raised(error, self._duration_ns, op_index=index, partial_output=list(self._outputs))


def member_of(job: ClassJob, index: int, op: str) -> Member:
    constructor = job.constructor
    if index == CONSTRUCTOR_INDEX:
        if op != constructor.name:
            raise CaseInputError(f'operation 0 must be "{constructor.name}", got "{op}"')
        return constructor
    method = job.methods.get(op)
    if method is None:
        raise CaseInputError(f'unknown operation "{op}" at index {index}')
    return method


def arguments_by_name(member: Member, args: Sequence[Json]) -> dict[str, Json]:
    if len(args) != len(member.params):
        raise CaseInputError(
            f'"{member.name}" takes {len(member.params)} arguments, the case gives {len(args)}'
        )
    return {param.name: value for param, value in zip(member.params, args, strict=True)}
