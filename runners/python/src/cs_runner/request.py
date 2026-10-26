"""The request file (docs/specs/runners.md#request-file and #bench-mode).

Signatures use canonical names; `names` gives the Python symbol of the function, class and each
method. Anything that cannot be run is a BadRequestError (exit code 2).
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import cast

from cs_runner.dsl import (
    ReturnType,
    TypeSyntaxError,
    ValueType,
    VoidType,
    parse_return_type,
    parse_value_type,
)
from cs_runner.errors import BadRequestError
from cs_runner.json_value import Json, is_int

PROTOCOL_VERSION = 1
CONCURRENT_KIND = "concurrent"
TEST_MODE = "test"
BENCH_MODE = "bench"
NANOSECONDS_PER_MILLISECOND = 1_000_000


class NodeSerialization(StrEnum):
    """The `as` modifier on a node-typed return."""

    VALUE = "value"
    INDEX = "index"


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    type: ValueType
    ref_of: str | None = None


@dataclass(frozen=True, slots=True)
class Returns:
    type: ReturnType
    output_from: str | None = None
    serialize_as: NodeSerialization | None = None
    index_of: str | None = None
    no_alias_with: str | None = None


@dataclass(frozen=True, slots=True)
class Member:
    """A function, constructor or method."""

    name: str
    """Canonical name, as in the signature and in operation sequences."""
    symbol: str
    """Python name in the target file."""
    params: tuple[Param, ...]
    returns: Returns

    def param(self, name: str) -> Param:
        return next(param for param in self.params if param.name == name)


@dataclass(frozen=True, slots=True)
class FunctionCase:
    case_id: str
    values: Mapping[str, Json]
    """Input values by canonical parameter name."""


@dataclass(frozen=True, slots=True)
class OperationCase:
    case_id: str
    ops: tuple[str, ...]
    args: tuple[tuple[Json, ...], ...]


@dataclass(frozen=True, slots=True)
class FunctionJob:
    job_id: str
    path: str
    function: Member
    cases: tuple[FunctionCase, ...]


@dataclass(frozen=True, slots=True)
class ClassJob:
    job_id: str
    path: str
    constructor: Member
    """Named after the class; `ops[0]` of every case."""
    methods: Mapping[str, Member]
    """By canonical name."""
    cases: tuple[OperationCase, ...]


class Model(StrEnum):
    """How a concurrent job's workers run (docs/specs/runners.md#concurrent-jobs)."""

    THREADS = "threads"
    ASYNC = "async"


class Granularity(StrEnum):
    """Where yields are injected inside the target file (threads model)."""

    LINE = "line"
    INSTRUCTION = "instruction"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class Script:
    """Ops with their arguments; worker and final scripts have no constructor."""

    ops: tuple[str, ...]
    args: tuple[tuple[Json, ...], ...]


@dataclass(frozen=True, slots=True)
class Perturbation:
    yield_probability: float
    max_yields: int
    granularity: Granularity


@dataclass(frozen=True, slots=True)
class StressCase:
    """One stress run: setup, worker scripts released together, then an optional final."""

    case_id: str
    seed: int
    """Already the case's seed plus the run index."""
    deadline_ns: int
    perturb: Perturbation
    setup: Script
    workers: tuple[Script, ...]
    final: Script | None


@dataclass(frozen=True, slots=True)
class ConcurrentJob:
    job_id: str
    path: str
    constructor: Member
    methods: Mapping[str, Member]
    model: Model
    cases: tuple["OperationCase | StressCase", ...]
    """Sequential cases first, then the stress runs."""

    def as_class_job(self) -> ClassJob:
        """The job without its cases, so sequential cases run like a design problem's."""
        return ClassJob(self.job_id, self.path, self.constructor, self.methods, ())


type SequentialJob = FunctionJob | ClassJob
"""Jobs whose cases run one call sequence at a time; bench targets are always one."""
type Job = SequentialJob | ConcurrentJob
type BenchCase = FunctionCase | OperationCase


@dataclass(frozen=True, slots=True)
class BenchTarget:
    target_id: str
    job: SequentialJob
    """The target as a job without cases, so it loads and runs like a test-mode job."""
    emits_output: bool
    """`output: true`: report the output of each size's first call (`bench_output`)."""


@dataclass(frozen=True, slots=True)
class BenchInput:
    size: int
    case: BenchCase
    max_batch: int
    """At most this many calls (each on a fresh copy of the input) per timed sample."""


@dataclass(frozen=True, slots=True)
class Warmup:
    min_runs: int
    max_runs: int
    cv: float
    """Stop once the coefficient of variation of the latest runs is at most this."""


@dataclass(frozen=True, slots=True)
class BenchSettings:
    reps: int
    warmup: Warmup
    budget_ns: int
    """One call above this stops the target at this and larger sizes."""
    memory: bool
    min_sample_ns: int
    """Fast calls are batched until one sample lasts at least this long."""


@dataclass(frozen=True, slots=True)
class BenchJob:
    job_id: str
    targets: tuple[BenchTarget, ...]
    inputs: tuple[BenchInput, ...]
    settings: BenchSettings


@dataclass(frozen=True, slots=True)
class TestRequest:
    jobs: tuple[Job, ...]


@dataclass(frozen=True, slots=True)
class BenchRequest:
    jobs: tuple[BenchJob, ...]


def parse_request(text: str) -> TestRequest | BenchRequest:
    try:
        document: object = json.loads(text)
    except ValueError as error:
        raise BadRequestError(f"request is not JSON: {error}") from None
    request = _Fields(document, "request")
    protocol = request.integer("protocol")
    if protocol != PROTOCOL_VERSION:
        raise BadRequestError(f"protocol {protocol} is not supported (expected {PROTOCOL_VERSION})")
    mode = request.string("mode")
    jobs = request.objects("jobs")
    if mode == TEST_MODE:
        return TestRequest(tuple(_job(job) for job in jobs))
    if mode == BENCH_MODE:
        return BenchRequest(tuple(_bench_job(job) for job in jobs))
    expected = f'"{TEST_MODE}" or "{BENCH_MODE}"'
    raise BadRequestError(f'mode "{mode}" is not supported (expected {expected})')


class _Fields:
    """Typed access to one JSON object of the request; failures name the field."""

    def __init__(self, data: object, location: str) -> None:
        if not isinstance(data, dict):
            raise BadRequestError(f"{location} must be an object")
        self._data = cast("dict[str, object]", data)
        self.location = location

    def has(self, key: str) -> bool:
        return self._data.get(key) is not None

    def value(self, key: str) -> object:
        if key not in self._data:
            raise BadRequestError(f'{self.location} lacks "{key}"')
        return self._data[key]

    def string(self, key: str) -> str:
        value = self.value(key)
        if not isinstance(value, str):
            raise BadRequestError(f"{self.location}.{key} must be a string")
        return value

    def optional_string(self, key: str) -> str | None:
        return self.string(key) if self.has(key) else None

    def integer(self, key: str) -> int:
        value = self.value(key)
        if not is_int(value):
            raise BadRequestError(f"{self.location}.{key} must be an integer")
        return value

    def number(self, key: str) -> float:
        value = self.value(key)
        if not (is_int(value) or isinstance(value, float)):
            raise BadRequestError(f"{self.location}.{key} must be a number")
        return float(value)

    def boolean(self, key: str) -> bool:
        value = self.value(key)
        if not isinstance(value, bool):
            raise BadRequestError(f"{self.location}.{key} must be true or false")
        return value

    def array(self, key: str) -> list[object]:
        value = self.value(key)
        if not isinstance(value, list):
            raise BadRequestError(f"{self.location}.{key} must be an array")
        return cast("list[object]", value)

    def object(self, key: str) -> "_Fields":
        return _Fields(self.value(key), f"{self.location}.{key}")

    def objects(self, key: str) -> list["_Fields"]:
        return [
            _Fields(item, f"{self.location}.{key}[{index}]")
            for index, item in enumerate(self.array(key))
        ]

    def json_object(self, key: str) -> dict[str, Json]:
        return cast("dict[str, Json]", self.object(key)._data)

    def strings(self, key: str) -> dict[str, str]:
        values = self.object(key)._data
        if not all(isinstance(value, str) for value in values.values()):
            raise BadRequestError(f"{self.location}.{key} must map names to strings")
        return cast("dict[str, str]", values)


@dataclass(frozen=True, slots=True)
class _JobParts:
    """What a test job or a bench target declares: one target with its names."""

    job_id: str
    target: _Fields
    names: _Fields
    signature: _Fields
    cases: tuple[_Fields, ...]


def _job(job: _Fields) -> Job:
    parts = _JobParts(
        job.string("job_id"),
        job.object("target"),
        job.object("names"),
        job.object("signature"),
        tuple(job.objects("cases")),
    )
    if job.string("kind") == CONCURRENT_KIND:
        return _concurrent_job(parts, _model(job))
    return _parser(job)(parts)


def _model(job: _Fields) -> Model:
    model = job.string("model")
    if model not in Model:
        raise BadRequestError(f'{job.location}.model "{model}" is not supported')
    return Model(model)


def _concurrent_job(parts: _JobParts, model: Model) -> ConcurrentJob:
    design = _class_job(replace(parts, cases=()))
    cases = tuple(
        _stress_case(case) if case.has("stress") else _operation_case(case, case.string("id"))
        for case in parts.cases
    )
    return ConcurrentJob(
        design.job_id, design.path, design.constructor, design.methods, model, cases
    )


def _stress_case(case: _Fields) -> StressCase:
    stress = case.object("stress")
    perturb = stress.object("perturb")
    granularity = perturb.string("python_granularity")
    if granularity not in Granularity:
        raise BadRequestError(f'{perturb.location}.python_granularity "{granularity}" is unknown')
    return StressCase(
        case_id=case.string("id"),
        seed=stress.integer("seed"),
        deadline_ns=stress.integer("deadline_ms") * NANOSECONDS_PER_MILLISECOND,
        perturb=Perturbation(
            perturb.number("yield_probability"),
            perturb.integer("max_yields"),
            Granularity(granularity),
        ),
        setup=_script(stress.object("setup")),
        workers=tuple(_script(worker) for worker in stress.objects("workers")),
        final=_script(stress.object("final")) if stress.has("final") else None,
    )


def _script(script: _Fields) -> Script:
    sequence = _operation_case(script, "")
    return Script(sequence.ops, sequence.args)


def _parser(job: _Fields) -> Callable[[_JobParts], SequentialJob]:
    kind = job.string("kind")
    parser = _JOB_PARSERS.get(kind)
    if parser is None:
        raise BadRequestError(f'{job.location}.kind "{kind}" is not supported')
    return parser


def _function_job(parts: _JobParts) -> FunctionJob:
    declared = parts.signature.object("function")
    function = Member(
        declared.string("name"),
        parts.names.string("function"),
        _params(declared),
        _returns(declared.object("returns")),
    )
    cases = tuple(
        FunctionCase(case.string("id"), case.json_object("input")) for case in parts.cases
    )
    return FunctionJob(parts.job_id, parts.target.string("path"), function, cases)


def _class_job(parts: _JobParts) -> ClassJob:
    declared = parts.signature.object("class")
    constructor = Member(
        declared.string("name"),
        parts.names.string("class"),
        _params(declared.object("constructor")),
        Returns(VoidType()),
    )
    symbols = parts.names.strings("methods")
    methods = (_method(method, symbols) for method in declared.objects("methods"))
    cases = tuple(_operation_case(case, case.string("id")) for case in parts.cases)
    return ClassJob(
        parts.job_id,
        parts.target.string("path"),
        constructor,
        {method.name: method for method in methods},
        cases,
    )


_JOB_PARSERS: Mapping[str, Callable[[_JobParts], SequentialJob]] = {
    "function": _function_job,
    "design": _class_job,
    "progressive": _class_job,
}


def _bench_job(job: _Fields) -> BenchJob:
    parser = _parser(job)
    job_id = job.string("job_id")
    signature = job.object("signature")
    targets = tuple(
        _bench_target(target, job_id, signature, parser) for target in job.objects("targets")
    )
    inputs = tuple(
        _bench_input(item, function_kind=parser is _function_job) for item in job.objects("inputs")
    )
    return BenchJob(job_id, targets, inputs, _bench_settings(job.object("settings")))


def _bench_target(
    target: _Fields, job_id: str, signature: _Fields, parser: Callable[[_JobParts], SequentialJob]
) -> BenchTarget:
    target_id = target.string("target_id")
    parts = _JobParts(
        f"{job_id}/{target_id}", target.object("target"), target.object("names"), signature, ()
    )
    return BenchTarget(target_id, parser(parts), target.has("output") and target.boolean("output"))


def _bench_input(item: _Fields, function_kind: bool) -> BenchInput:
    size = item.integer("size")
    case_id = f"n={size}"
    case: BenchCase = (
        FunctionCase(case_id, item.json_object("input"))
        if function_kind
        else _operation_case(item, case_id)
    )
    return BenchInput(size, case, item.integer("max_batch"))


def _bench_settings(settings: _Fields) -> BenchSettings:
    warmup = settings.object("warmup")
    return BenchSettings(
        reps=settings.integer("reps"),
        warmup=Warmup(warmup.integer("min"), warmup.integer("max"), warmup.number("cv")),
        budget_ns=settings.integer("budget_ms") * NANOSECONDS_PER_MILLISECOND,
        memory=settings.boolean("memory"),
        min_sample_ns=settings.integer("min_sample_ns"),
    )


def _method(method: _Fields, symbols: Mapping[str, str]) -> Member:
    name = method.string("name")
    symbol = symbols.get(name)
    if symbol is None:
        raise BadRequestError(f'names.methods lacks "{name}"')
    return Member(name, symbol, _params(method), _returns(method.object("returns")))


def _params(member: _Fields) -> tuple[Param, ...]:
    return tuple(
        Param(
            param.string("name"),
            _value_type(param.string("type"), param.location),
            param.optional_string("ref_of"),
        )
        for param in member.objects("params")
    )


def _returns(returns: _Fields) -> Returns:
    serialize_as = _serialization(returns)
    index_of = returns.optional_string("of")
    if serialize_as is NodeSerialization.INDEX and index_of is None:
        raise BadRequestError(f'{returns.location} has "as: index" without "of"')
    return Returns(
        _return_type(returns.string("type"), returns.location),
        returns.optional_string("output_from"),
        serialize_as,
        index_of,
        returns.optional_string("no_alias_with"),
    )


def _serialization(returns: _Fields) -> NodeSerialization | None:
    serialize_as = returns.optional_string("as")
    if serialize_as is None:
        return None
    if serialize_as not in NodeSerialization:
        raise BadRequestError(f'{returns.location}.as "{serialize_as}" is not supported')
    return NodeSerialization(serialize_as)


def _operation_case(case: _Fields, case_id: str) -> OperationCase:
    ops = case.array("ops")
    args = case.array("args")
    if not all(isinstance(op, str) for op in ops):
        raise BadRequestError(f"{case.location}.ops must hold operation names")
    if len(args) != len(ops) or not all(isinstance(arguments, list) for arguments in args):
        raise BadRequestError(f"{case.location}.args must hold one argument array per operation")
    arguments = cast("list[list[Json]]", args)
    return OperationCase(
        case_id,
        tuple(cast("list[str]", ops)),
        tuple(tuple(values) for values in arguments),
    )


def _value_type(text: str, location: str) -> ValueType:
    try:
        return parse_value_type(text)
    except TypeSyntaxError as error:
        raise BadRequestError(f"{location}: {error}") from None


def _return_type(text: str, location: str) -> ReturnType:
    try:
        return parse_return_type(text)
    except TypeSyntaxError as error:
        raise BadRequestError(f"{location}: {error}") from None
