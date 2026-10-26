"""Maps the schema-valid `concurrency` block of meta.yaml and the `stress` objects of tests.json
onto the domain model (docs/specs/problem-format.md#concurrent-problems).

The schemas guarantee shapes and value ranges; nothing here re-validates them.
"""

from collections.abc import Mapping, Sequence
from typing import Any, cast

from coding_study.domain.cases import JsonValue, OperationSequence
from coding_study.domain.concurrency import (
    DEFAULT_DEADLINE_MS,
    DEFAULT_RUNS,
    BrokenReference,
    Concurrency,
    ConcurrencyModel,
    Perturbation,
    PerturbationOverride,
    PythonGranularity,
    ThreadKind,
)
from coding_study.domain.problem import Language
from coding_study.domain.stress import (
    DEFAULT_STRESS_SEED,
    OUTPUT,
    ArithmeticSequence,
    Bounds,
    CheckerInvariant,
    Count,
    Distinct,
    EqualMultisets,
    FinalSequence,
    Invariant,
    Literal,
    Pick,
    RandomInteger,
    Repeat,
    Scope,
    SectionBounds,
    Selector,
    SourceOrder,
    Step,
    StressScenario,
    Sum,
    Template,
    WorkerGroup,
)

type Document = Mapping[str, Any]


def concurrency_from_document(document: Document, languages: tuple[Language, ...]) -> Concurrency:
    model = document["model"]
    models = (
        dict.fromkeys(languages, ConcurrencyModel(model))
        if isinstance(model, str)
        else {Language(name): ConcurrencyModel(value) for name, value in model.items()}
    )
    return Concurrency(
        models=models,
        jvm_threads=tuple(ThreadKind(kind) for kind in document.get("jvm_threads", ["platform"])),
        runs=document.get("runs", DEFAULT_RUNS),
        deadline_ms=document.get("deadline_ms", DEFAULT_DEADLINE_MS),
        perturb=_override(document.get("perturb", {})).applied_to(Perturbation()),
        broken=tuple(_broken(entry) for entry in document.get("broken", ())),
    )


def stress_from_document(document: Document) -> StressScenario:
    final = document.get("final")
    return StressScenario(
        setup=_sequence(document["setup"]),
        workers=tuple(_group(group) for group in document["workers"]),
        invariants=tuple(_invariant(invariant) for invariant in document.get("invariants", ())),
        final=_final(final) if final is not None else None,
        seed=document.get("seed", DEFAULT_STRESS_SEED),
        deadline_ms=document.get("deadline_ms"),
        perturb=_override(document.get("perturb", {})),
        document=cast("dict[str, JsonValue]", dict(document)),
    )


def _broken(entry: Document) -> BrokenReference:
    languages = entry.get("languages")
    return BrokenReference(
        id=entry["id"],
        name=entry["name"],
        bug=entry["bug"],
        caught_by=tuple(entry["caught_by"]),
        languages=tuple(Language(name) for name in languages) if languages else None,
    )


def _override(perturb: Document) -> PerturbationOverride:
    granularity = perturb.get("python_granularity")
    return PerturbationOverride(
        yield_probability=perturb.get("yield_probability"),
        max_yields=perturb.get("max_yields"),
        python_granularity=PythonGranularity(granularity) if granularity else None,
    )


def _sequence(document: Document) -> OperationSequence:
    return OperationSequence(
        tuple(document["ops"]), tuple(tuple(args) for args in document["args"])
    )


def _final(document: Document) -> FinalSequence:
    expected = document.get("expected")
    return FinalSequence(
        ops=tuple(document["ops"]),
        args=tuple(tuple(args) for args in document["args"]),
        expected=tuple(expected) if expected is not None else None,
    )


def _group(document: Document) -> WorkerGroup:
    is_mix = "mix" in document
    steps: Sequence[Document] = document["mix"] if is_mix else document["steps"]
    return WorkerGroup(
        group=document["group"],
        count=document["count"],
        repeat=_repeat(document["repeat"]),
        steps=tuple(_step(step) for step in steps),
        is_mix=is_mix,
    )


def _repeat(repeat: int | Document) -> Repeat:
    if isinstance(repeat, int):
        return Repeat(repeat)
    per_language = {Language(name): value for name, value in repeat.items() if name != "default"}
    return Repeat(repeat["default"], per_language)


def _step(document: Document) -> Step:
    return Step(
        op=document["op"],
        args=tuple(_template(argument) for argument in document["args"]),
        weight=document.get("weight", 1),
    )


def _template(argument: JsonValue) -> Template:
    if not isinstance(argument, dict) or len(argument) != 1:
        return Literal(argument)
    ((key, value),) = argument.items()
    match key:
        case "$seq":
            fields = cast("dict[str, int]", value)
            return ArithmeticSequence(
                fields["start"], fields.get("worker_stride", 0), fields.get("step", 1)
            )
        case "$rand":
            low, high = cast("list[int]", value)
            return RandomInteger(low, high)
        case "$pick":
            return Pick(tuple(cast("list[JsonValue]", value)))
        case _:
            return Literal(argument)


def _selector(document: Document) -> Selector:
    return Selector(
        op=document["op"],
        of=document.get("of", OUTPUT),
        group=document.get("group"),
        scope=Scope(document.get("scope", Scope.ALL)),
    )


def _invariant(document: Document) -> Invariant:
    match document["type"]:
        case "equal_multisets":
            return EqualMultisets(_selector(document["left"]), _selector(document["right"]))
        case "distinct":
            return Distinct(_selector(document["values"]))
        case "bounds":
            return Bounds(_selector(document["values"]), document.get("min"), document.get("max"))
        case "count":
            return Count(
                _selector(document["values"]),
                document.get("equals"),
                document.get("min"),
                document.get("max"),
            )
        case "sum":
            return Sum(_selector(document["values"]), document.get("min"), document.get("max"))
        case "source_order":
            return SourceOrder(_selector(document["values"]), document["stride"])
        case "section":
            return SectionBounds(
                document["name"],
                document.get("max_violations", 0),
                document.get("min_occupancy"),
                document.get("max_occupancy"),
            )
        case _:
            return CheckerInvariant(document["name"])
