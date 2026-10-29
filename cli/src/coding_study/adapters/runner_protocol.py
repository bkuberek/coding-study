"""The runner wire format (docs/specs/runners.md): the request file and the JSON Lines events.

Every runner speaks this format; only `SubprocessRunner` reads and writes it.
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import NoReturn, cast

from coding_study.domain.bench_runs import (
    BenchInput,
    BenchRequest,
    BenchSample,
    BenchSettings,
    BenchTarget,
    MemoryMeasurement,
)
from coding_study.domain.cases import FunctionInput, JsonValue
from coding_study.domain.errors import RunnerProtocolError
from coding_study.domain.naming import FunctionNames, SymbolNames
from coding_study.domain.runs import (
    PROTOCOL_VERSION,
    ClassTarget,
    CompiledTarget,
    FileTarget,
    InvalidOutput,
    Raised,
    RequestInput,
    Returned,
    RunCase,
    RunJob,
    RunMode,
    RunnerInfo,
    RunRequest,
    RunTarget,
    SectionCounters,
    Stalled,
    StressCompleted,
    StressFailure,
    StressPhase,
    StressRun,
    UserError,
    WorkerProgress,
)
from coding_study.domain.signature import FunctionSignature, Param, Returns, Signature

type JsonObject = dict[str, JsonValue]

MAX_QUOTED_LINE_LENGTH = 200
DEFAULT_SAMPLE_CALLS = 1


@dataclass(frozen=True, slots=True)
class Hello:
    runner: str
    protocol: int
    runtime: str
    features: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class JobStart:
    job_id: str


@dataclass(frozen=True, slots=True)
class CaseStart:
    job_id: str
    case_id: str


type ReportedOutcome = Returned | Raised | InvalidOutput | StressCompleted | Stalled


@dataclass(frozen=True, slots=True)
class CaseResult:
    job_id: str
    case_id: str
    outcome: ReportedOutcome


@dataclass(frozen=True, slots=True)
class RestartRequested:
    """Written after a stress run's `case_result` when worker threads are still alive; the
    runner then exits with code 3 and the CLI restarts it for the remaining cases."""

    reason: str


@dataclass(frozen=True, slots=True)
class LoadError:
    """Test mode: replaces every `case_*` event of the job. Bench mode: one target did not load."""

    job_id: str
    error: UserError
    target_id: str | None = None


@dataclass(frozen=True, slots=True)
class JobEnd:
    job_id: str


@dataclass(frozen=True, slots=True)
class Bye:
    pass


@dataclass(frozen=True, slots=True)
class BenchStart:
    """A call, or a batch of calls, of one target at one size is about to run."""

    job_id: str
    target_id: str
    size: int


@dataclass(frozen=True, slots=True)
class BenchOutputEvent:
    job_id: str
    target_id: str
    size: int
    output: JsonValue


@dataclass(frozen=True, slots=True)
class BenchError:
    """The target failed at this size and is not run further."""

    job_id: str
    target_id: str
    size: int
    outcome: Raised | InvalidOutput


@dataclass(frozen=True, slots=True)
class BenchSampleEvent:
    job_id: str
    target_id: str
    size: int
    sample: BenchSample


@dataclass(frozen=True, slots=True)
class BenchMemory:
    job_id: str
    target_id: str
    size: int
    memory: MemoryMeasurement


@dataclass(frozen=True, slots=True)
class BenchBudgetExceeded:
    job_id: str
    target_id: str
    size: int
    wall_ns: int


type BenchEvent = (
    BenchStart
    | BenchOutputEvent
    | BenchError
    | BenchSampleEvent
    | BenchMemory
    | BenchBudgetExceeded
)
type RunnerEvent = (
    Hello
    | JobStart
    | CaseStart
    | CaseResult
    | LoadError
    | JobEnd
    | Bye
    | RestartRequested
    | BenchEvent
)


def encode_request(request: RunRequest) -> JsonObject:
    return {
        "protocol": PROTOCOL_VERSION,
        "mode": RunMode.TEST.value,
        "jobs": [_job(job) for job in request.jobs],
    }


def encode_bench_request(request: BenchRequest) -> JsonObject:
    job = request.job
    return {
        "protocol": PROTOCOL_VERSION,
        "mode": RunMode.BENCH.value,
        "jobs": [
            {
                "job_id": job.job_id,
                "kind": job.kind.value,
                "signature": _signature(job.signature),
                "targets": [_bench_target(target) for target in job.targets],
                "inputs": [_bench_input(bench_input) for bench_input in job.inputs],
                "settings": _bench_settings(job.settings),
            }
        ],
    }


def accepted_hello(hello: Hello, said_hello: bool) -> RunnerInfo:
    """The runner's identity; a second hello or another protocol version is a protocol error."""
    if said_hello:
        raise RunnerProtocolError("runner said hello twice")
    if hello.protocol != PROTOCOL_VERSION:
        raise RunnerProtocolError(
            f"runner speaks protocol {hello.protocol}; the CLI speaks {PROTOCOL_VERSION}"
        )
    return RunnerInfo(hello.runner, hello.protocol, hello.runtime, hello.features)


def decode_event(line: str) -> RunnerEvent:
    """One line of the `--out` file; raises RunnerProtocolError when it is not a valid event."""
    fields = _Fields(_parse_object(line), line)
    name = fields.string("event")
    decoder = _EVENT_DECODERS.get(name)
    if decoder is None:
        fields.fail(f'unknown event "{name}"')
    return decoder(fields)


def _job(job: RunJob) -> JsonObject:
    encoded: JsonObject = {
        "job_id": job.job_id,
        "kind": job.kind.value,
        "target": _target(job.target),
        "names": _names(job.names),
        "signature": _signature(job.signature),
        "cases": [_case(case) for case in job.cases],
    }
    if job.model is not None:
        encoded["model"] = job.model.value
    return encoded


def _target(target: RunTarget) -> JsonObject:
    match target:
        case FileTarget(path):
            return {"path": path}
        case ClassTarget(class_name):
            return {"class": class_name}
        case CompiledTarget(id):
            return {"compiled": id}


def _names(names: SymbolNames) -> JsonObject:
    if isinstance(names, FunctionNames):
        return {"function": names.function, "params": dict(names.params)}
    return {"class": names.class_name, "methods": dict(names.methods)}


def _signature(signature: Signature) -> JsonObject:
    if isinstance(signature, FunctionSignature):
        return {
            "function": {
                "name": signature.name,
                "params": _params(signature.params),
                "returns": _returns(signature.returns),
            }
        }
    methods: list[JsonValue] = []
    for method in signature.methods:
        encoded: JsonObject = {
            "name": method.name,
            "params": _params(method.params),
            "returns": _returns(method.returns),
        }
        if method.level is not None:
            encoded["level"] = method.level
        if method.blocking:
            encoded["blocking"] = True
        methods.append(encoded)
    return {
        "class": {
            "name": signature.name,
            "constructor": {"params": _params(signature.constructor_params)},
            "methods": methods,
        }
    }


def _params(params: tuple[Param, ...]) -> list[JsonValue]:
    return [_present({"name": p.name, "type": str(p.type), "ref_of": p.ref_of}) for p in params]


def _returns(returns: Returns) -> JsonObject:
    serialize_as = returns.serialize_as.value if returns.serialize_as is not None else None
    return _present(
        {
            "type": str(returns.type),
            "output_from": returns.output_from,
            "as": serialize_as,
            "of": returns.index_of,
            "no_alias_with": returns.no_alias_with,
        }
    )


def _present(fields: JsonObject) -> JsonObject:
    """Drops unset modifiers so the signature reads like meta.yaml."""
    return {key: value for key, value in fields.items() if value is not None}


def _case(case: RunCase) -> JsonObject:
    return {"id": case.id, **_input(case.input)}


def _input(run_input: RequestInput) -> JsonObject:
    match run_input:
        case FunctionInput(arguments=arguments):
            return {"input": dict(arguments)}
        case StressRun():
            return {"stress": _stress(run_input)}
        case _:
            return _sequence(run_input.ops, run_input.args)


def _sequence(ops: tuple[str, ...], args: tuple[tuple[JsonValue, ...], ...]) -> JsonObject:
    return {"ops": list(ops), "args": [list(arguments) for arguments in args]}


def _stress(run: StressRun) -> JsonObject:
    perturb = run.perturb
    encoded: JsonObject = {
        "seed": run.seed,
        "deadline_ms": run.deadline_ms,
        "perturb": {
            "yield_probability": perturb.yield_probability,
            "max_yields": perturb.max_yields,
            "python_granularity": perturb.python_granularity.value,
        },
        "setup": _sequence(run.setup.ops, run.setup.args),
        "workers": [_sequence(worker.ops, worker.args) for worker in run.workers],
    }
    if run.thread_kind is not None:
        encoded["thread_kind"] = run.thread_kind.value
    if run.final is not None:
        encoded["final"] = _sequence(run.final.ops, run.final.args)
    return encoded


def _bench_target(target: BenchTarget) -> JsonObject:
    encoded: JsonObject = {
        "target_id": target.target_id,
        "target": _target(target.target),
        "names": _names(target.names),
    }
    if target.emits_output:
        encoded["output"] = True
    return encoded


def _bench_input(bench_input: BenchInput) -> JsonObject:
    return {
        "size": bench_input.size,
        **_input(bench_input.input),
        "max_batch": bench_input.max_batch,
    }


def _bench_settings(settings: BenchSettings) -> JsonObject:
    warmup = settings.warmup
    return {
        "reps": settings.reps,
        "warmup": {"min": warmup.min_runs, "max": warmup.max_runs, "cv": warmup.cv},
        "budget_ms": settings.budget_ms,
        "memory": settings.memory,
        "min_sample_ns": settings.min_sample_ns,
    }


def _parse_object(line: str) -> Mapping[str, object]:
    try:
        parsed: object = json.loads(line, parse_constant=_reject_constant)
    except ValueError:
        _fail(line, "not JSON")
    if not isinstance(parsed, dict):
        _fail(line, "not a JSON object")
    return cast("dict[str, object]", parsed)


def _reject_constant(constant: str) -> NoReturn:
    raise ValueError(f"{constant} is not valid JSON")


def _fail(line: str, reason: str) -> NoReturn:
    quoted = line[:MAX_QUOTED_LINE_LENGTH]
    raise RunnerProtocolError(f"invalid runner event ({reason}): {quoted}")


class _Fields:
    """Typed access to an event's fields; every failure names the offending line."""

    def __init__(self, data: Mapping[str, object], line: str) -> None:
        self._data = data
        self._line = line

    def fail(self, reason: str) -> NoReturn:
        _fail(self._line, reason)

    def value(self, key: str) -> JsonValue:
        if key not in self._data:
            self.fail(f'missing "{key}"')
        return cast("JsonValue", self._data[key])

    def string(self, key: str) -> str:
        value = self.value(key)
        if not isinstance(value, str):
            self.fail(f'"{key}" must be a string')
        return value

    def optional_string(self, key: str) -> str:
        return self.string(key) if key in self._data else ""

    def integer(self, key: str) -> int:
        value = self.value(key)
        if isinstance(value, bool) or not isinstance(value, int):
            self.fail(f'"{key}" must be an integer')
        return value

    def optional_integer(self, key: str) -> int | None:
        return self.integer(key) if key in self._data else None

    def array(self, key: str) -> tuple[JsonValue, ...]:
        value = self.value(key)
        if not isinstance(value, list):
            self.fail(f'"{key}" must be an array')
        return tuple(value)

    def optional_array(self, key: str) -> tuple[JsonValue, ...]:
        return self.array(key) if key in self._data else ()

    def object(self, key: str) -> "_Fields":
        value = self.value(key)
        if not isinstance(value, dict):
            self.fail(f'"{key}" must be an object')
        return _Fields(value, self._line)

    def has(self, key: str) -> bool:
        return key in self._data

    def field_names(self) -> tuple[str, ...]:
        return tuple(self._data)

    def element(self, key: str, index: int) -> "_Fields":
        """Item `index` of the array `key`, which must be an object."""
        value = self.array(key)[index]
        if not isinstance(value, dict):
            self.fail(f'"{key}[{index}]" must be an object')
        return _Fields(value, self._line)


def _hello(fields: _Fields) -> Hello:
    features = fields.optional_array("features")
    if not all(isinstance(feature, str) for feature in features):
        fields.fail('"features" must hold strings')
    return Hello(
        fields.string("runner"),
        fields.integer("protocol"),
        fields.string("runtime"),
        tuple(str(feature) for feature in features),
    )


def _case_result(fields: _Fields) -> CaseResult:
    job_id, case_id = fields.string("job_id"), fields.string("case_id")
    status = fields.string("status")
    decoder = _OUTCOME_DECODERS.get(status)
    if decoder is None:
        fields.fail(f'unknown case status "{status}"')
    return CaseResult(job_id, case_id, decoder(fields))


def _returned(fields: _Fields) -> Returned | StressCompleted:
    """A stress run's `ok` carries `sections`; its output holds setup, workers and final."""
    if fields.has("sections"):
        return _stress_completed(fields)
    return Returned(
        fields.value("output"), fields.integer("duration_ns"), fields.optional_string("stdout")
    )


def _stress_completed(fields: _Fields) -> StressCompleted:
    output = fields.object("output")
    workers = output.array("workers")
    if not all(isinstance(worker, list) for worker in workers):
        fields.fail('"output.workers" must hold one array per worker')
    sections = fields.object("sections")
    return StressCompleted(
        setup=output.array("setup"),
        workers=tuple(tuple(cast("list[JsonValue]", worker)) for worker in workers),
        final=output.array("final"),
        sections={name: _section(sections.object(name)) for name in sections.field_names()},
        duration_ns=fields.integer("duration_ns"),
        stdout=fields.optional_string("stdout"),
    )


def _section(fields: _Fields) -> SectionCounters:
    return SectionCounters(
        fields.integer("entries"), fields.integer("violations"), fields.integer("max_occupancy")
    )


def _raised(fields: _Fields) -> Raised:
    return Raised(
        error=_user_error(fields.object("error")),
        duration_ns=fields.integer("duration_ns"),
        stdout=fields.optional_string("stdout"),
        op_index=fields.optional_integer("op_index"),
        partial_output=fields.optional_array("partial_output"),
        stress=_stress_failure(fields),
    )


def _invalid_output(fields: _Fields) -> InvalidOutput:
    return InvalidOutput(
        fields.string("reason"),
        fields.integer("duration_ns"),
        fields.optional_string("stdout"),
        _stress_failure(fields),
    )


def _stress_failure(fields: _Fields) -> StressFailure | None:
    """Stress runs name the phase that failed; other cases have no `phase`."""
    if not fields.has("phase"):
        return None
    phase = fields.string("phase")
    if phase not in StressPhase:
        fields.fail(f'unknown phase "{phase}"')
    return StressFailure(
        StressPhase(phase),
        fields.integer("op_index"),
        fields.optional_integer("worker"),
        _progress(fields),
    )


def _stalled(fields: _Fields) -> Stalled:
    return Stalled(
        _progress(fields), fields.integer("duration_ns"), fields.optional_string("stdout")
    )


def _progress(fields: _Fields) -> tuple[WorkerProgress, ...]:
    progress: list[WorkerProgress] = []
    for index in range(len(fields.optional_array("progress"))):
        item = fields.element("progress", index)
        in_op = item.value("in_op")
        if not isinstance(in_op, bool):
            item.fail('"in_op" must be true or false')
        progress.append(WorkerProgress(item.integer("worker"), item.integer("completed"), in_op))
    return tuple(progress)


def _load_error(fields: _Fields) -> LoadError:
    target_id = fields.optional_string("target_id") or None
    return LoadError(fields.string("job_id"), _user_error(fields.object("error")), target_id)


def _user_error(fields: _Fields) -> UserError:
    return UserError(
        fields.string("type"), fields.string("message"), fields.optional_string("trace")
    )


@dataclass(frozen=True, slots=True)
class _BenchPoint:
    job_id: str
    target_id: str
    size: int


def _bench_point(fields: _Fields) -> _BenchPoint:
    return _BenchPoint(fields.string("job_id"), fields.string("target_id"), fields.integer("size"))


def _bench_start(fields: _Fields) -> BenchStart:
    point = _bench_point(fields)
    return BenchStart(point.job_id, point.target_id, point.size)


def _bench_output(fields: _Fields) -> BenchOutputEvent:
    point = _bench_point(fields)
    return BenchOutputEvent(point.job_id, point.target_id, point.size, fields.value("output"))


def _bench_error(fields: _Fields) -> BenchError:
    point = _bench_point(fields)
    status = fields.string("status")
    decoder = _FAILURE_DECODERS.get(status)
    if decoder is None:
        fields.fail(f'unknown bench_error status "{status}"')
    return BenchError(point.job_id, point.target_id, point.size, decoder(fields))


def _bench_sample(fields: _Fields) -> BenchSampleEvent:
    point = _bench_point(fields)
    calls = fields.optional_integer("calls") or DEFAULT_SAMPLE_CALLS
    sample = BenchSample(
        fields.integer("rep"), fields.integer("wall_ns"), fields.integer("cpu_ns"), calls
    )
    return BenchSampleEvent(point.job_id, point.target_id, point.size, sample)


def _bench_memory(fields: _Fields) -> BenchMemory:
    point = _bench_point(fields)
    memory = MemoryMeasurement(fields.string("metric"), fields.integer("bytes"))
    return BenchMemory(point.job_id, point.target_id, point.size, memory)


def _bench_budget_exceeded(fields: _Fields) -> BenchBudgetExceeded:
    point = _bench_point(fields)
    return BenchBudgetExceeded(point.job_id, point.target_id, point.size, fields.integer("wall_ns"))


_OUTCOME_DECODERS: Mapping[str, Callable[[_Fields], ReportedOutcome]] = {
    "ok": _returned,
    "error": _raised,
    "invalid_output": _invalid_output,
    "stalled": _stalled,
}
_FAILURE_DECODERS: Mapping[str, Callable[[_Fields], Raised | InvalidOutput]] = {
    "error": _raised,
    "invalid_output": _invalid_output,
}
_EVENT_DECODERS: Mapping[str, Callable[[_Fields], RunnerEvent]] = {
    "bench_start": _bench_start,
    "bench_output": _bench_output,
    "bench_error": _bench_error,
    "bench_sample": _bench_sample,
    "bench_memory": _bench_memory,
    "bench_budget_exceeded": _bench_budget_exceeded,
    "hello": _hello,
    "job_start": lambda fields: JobStart(fields.string("job_id")),
    "case_start": lambda fields: CaseStart(fields.string("job_id"), fields.string("case_id")),
    "case_result": _case_result,
    "load_error": _load_error,
    "job_end": lambda fields: JobEnd(fields.string("job_id")),
    "restart_requested": lambda fields: RestartRequested(fields.optional_string("reason")),
    "bye": lambda _fields: Bye(),
}
