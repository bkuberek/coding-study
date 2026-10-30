"""Maps schema-valid meta.yaml and tests.json documents onto the domain model.

The schemas already guarantee shapes and value sets; this module parses type DSL strings and
enforces the rules a JSON Schema cannot express (unique ids, required expected values, modifiers
that must name existing parameters).
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from coding_study.adapters.concurrency_documents import (
    concurrency_from_document,
    stress_from_document,
)
from coding_study.domain.cases import (
    Case,
    CaseInput,
    Expected,
    FunctionInput,
    GeneratedInput,
    OperationSequence,
)
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.problem import (
    ALL_LANGUAGES,
    DEFAULT_BUDGET_MS,
    DEFAULT_CURRICULUM_ORDER,
    DEFAULT_FLOAT_TOLERANCE,
    DEFAULT_SIZE_LADDER,
    Approach,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ComplexityClass,
    ContentStatus,
    Difficulty,
    Language,
    LeetCodeReference,
    Level,
    Perf,
    ProblemKind,
    ProblemMeta,
    References,
    StubSource,
    Track,
)
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    NodeSerialization,
    Param,
    Returns,
    Signature,
    blocking_issues,
    modifier_issues,
)
from coding_study.domain.stress import StressScenario
from coding_study.domain.time_limits import AbsoluteTimeLimit, FactorTimeLimit, TimeLimit
from coding_study.domain.type_dsl import TypeSyntaxError, parse_return_type, parse_value_type

type Document = Mapping[str, Any]


class _DocumentError(Exception):
    def __init__(self, location: str, message: str) -> None:
        super().__init__(message)
        self.location = location
        self.message = message


def meta_from_document(document: Document, source: str) -> ProblemMeta:
    """`source` is the repository-relative file name used in reported issues."""
    try:
        meta = _meta(document)
    except _DocumentError as issue:
        raise ContentError([ContentIssue(source, issue.location, issue.message)]) from None
    issues = modifier_issues(meta.signature)
    if meta.kind is not ProblemKind.CONCURRENT:
        issues += blocking_issues(meta.signature)
    if issues:
        raise ContentError(
            [ContentIssue(source, issue.location, issue.message) for issue in issues]
        )
    return meta


def cases_from_document(
    document: Document, comparator: ComparatorSpec, source: str
) -> tuple[Case, ...]:
    try:
        return _cases(document["cases"], comparator)
    except _DocumentError as issue:
        raise ContentError([ContentIssue(source, issue.location, issue.message)]) from None


def _meta(document: Document) -> ProblemMeta:
    languages = tuple(Language(name) for name in document.get("languages", ALL_LANGUAGES))
    concurrency = document.get("concurrency")
    return ProblemMeta(
        id=document["id"],
        slug=document["slug"],
        title=document["title"],
        status=ContentStatus(document["status"]),
        difficulty=Difficulty(document["difficulty"]),
        track=Track(document["track"]),
        kind=ProblemKind(document["kind"]),
        signature=_signature(document["signature"]),
        comparator=_comparator(document["comparator"]),
        approaches=_approaches(document["approaches"]),
        patterns=tuple(document.get("patterns", ())),
        languages=languages,
        stub=StubSource(document.get("stub", StubSource.GENERATED)),
        levels=tuple(Level(level["level"], level["title"]) for level in document.get("levels", ())),
        perf=_perf(document.get("perf", {})),
        hang_guard_ms=document.get("limits", {}).get("hang_guard_ms"),
        references=_references(document.get("references", {})),
        related=tuple(document.get("related", ())),
        order=document.get("order", DEFAULT_CURRICULUM_ORDER),
        estimate_minutes=document.get("estimate_minutes"),
        concurrency=(
            concurrency_from_document(concurrency, languages) if concurrency is not None else None
        ),
    )


def _signature(signature: Document) -> Signature:
    if "function" in signature:
        return _function(signature["function"], "signature.function")
    return _class(signature["class"], "signature.class")


def _function(function: Document, location: str) -> FunctionSignature:
    return FunctionSignature(
        name=function["name"],
        params=_params(function["params"], f"{location}.params"),
        returns=_returns(function["returns"], f"{location}.returns"),
    )


def _class(class_document: Document, location: str) -> ClassSignature:
    methods = class_document["methods"]
    return ClassSignature(
        name=class_document["name"],
        constructor_params=_params(
            class_document["constructor"]["params"], f"{location}.constructor.params"
        ),
        methods=tuple(
            _method(method, f"{location}.methods[{index}]") for index, method in enumerate(methods)
        ),
    )


def _method(method: Document, location: str) -> Method:
    return Method(
        name=method["name"],
        params=_params(method["params"], f"{location}.params"),
        returns=_returns(method["returns"], f"{location}.returns"),
        level=method.get("level"),
        blocking=method.get("blocking", False),
    )


def _params(params: Sequence[Document], location: str) -> tuple[Param, ...]:
    return tuple(
        Param(
            name=param["name"],
            type=_parsed_type(parse_value_type, param["type"], f"{location}[{index}].type"),
            ref_of=param.get("ref_of"),
        )
        for index, param in enumerate(params)
    )


def _returns(returns: Document, location: str) -> Returns:
    serialize_as = returns.get("as")
    return Returns(
        type=_parsed_type(parse_return_type, returns["type"], f"{location}.type"),
        output_from=returns.get("output_from"),
        serialize_as=NodeSerialization(serialize_as) if serialize_as is not None else None,
        index_of=returns.get("of"),
        no_alias_with=returns.get("no_alias_with"),
    )


def _parsed_type[T](parse: Callable[[str], T], text: str, location: str) -> T:
    try:
        return parse(text)
    except TypeSyntaxError as error:
        raise _DocumentError(location, str(error)) from error


def _comparator(comparator: Document) -> ComparatorSpec:
    per_method = comparator.get("per_method", {})
    return ComparatorSpec(
        type=ComparatorType(comparator["type"]),
        tolerance=comparator.get("tolerance", DEFAULT_FLOAT_TOLERANCE),
        per_method={method: ComparatorType(name) for method, name in per_method.items()},
    )


def _approaches(approaches: Sequence[Document]) -> tuple[Approach, ...]:
    _reject_duplicate_ids(approaches, "approaches", "approach id")
    return tuple(
        Approach(
            id=approach["id"],
            name=approach["name"],
            role=ApproachRole(approach["role"]),
            time=approach["time"],
            space=approach["space"],
            time_class=_complexity_class(approach.get("time_class")),
            space_class=_complexity_class(approach.get("space_class")),
            oracle=approach.get("oracle", False),
            languages=_languages(approach.get("languages")),
        )
        for approach in approaches
    )


def _languages(names: Sequence[str] | None) -> tuple[Language, ...] | None:
    return tuple(Language(name) for name in names) if names else None


def _complexity_class(name: str | None) -> ComplexityClass | None:
    return ComplexityClass(name) if name is not None else None


def _perf(perf: Document) -> Perf:
    return Perf(
        size_param=perf.get("size_param"),
        size_ladder=tuple(perf.get("size_ladder", DEFAULT_SIZE_LADDER)),
        budget_ms=perf.get("budget_ms", DEFAULT_BUDGET_MS),
        expected_from=perf.get("expected_from"),
        time_limit=_time_limit(perf.get("time_limit")),
    )


def _time_limit(time_limit: Document | None) -> TimeLimit | None:
    if time_limit is None:
        return None
    if "factor" in time_limit:
        return FactorTimeLimit(time_limit["factor"])
    return AbsoluteTimeLimit(time_limit["ms"])


def _references(references: Document) -> References:
    leetcode = references.get("leetcode")
    return References(
        leetcode=LeetCodeReference(leetcode["number"], leetcode["url"]) if leetcode else None,
        links=tuple(references.get("links", ())),
    )


def _cases(cases: Sequence[Document], comparator: ComparatorSpec) -> tuple[Case, ...]:
    _reject_duplicate_ids(cases, "cases", "case id")
    return tuple(_case(case, comparator, f"cases[{index}]") for index, case in enumerate(cases))


def _case(case: Document, comparator: ComparatorSpec, location: str) -> Case:
    case_input = _case_input(case)
    expected = Expected(case["expected"]) if "expected" in case else None
    if expected is None and _requires_expected(case_input, comparator):
        raise _DocumentError(
            location, "missing expected (required unless generated or the comparator is checker)"
        )
    return Case(
        id=case["id"],
        input=case_input,
        expected=expected,
        visible=case.get("visible", False),
        level=case.get("level"),
        hang_guard_ms=case.get("hang_guard_ms"),
        note=case.get("note"),
    )


def _case_input(case: Document) -> CaseInput:
    if "stress" in case:
        return stress_from_document(case["stress"])
    if "generate" in case:
        return GeneratedInput(n=case["generate"]["n"], seed=case["generate"]["seed"])
    if "ops" in case:
        return OperationSequence(
            ops=tuple(case["ops"]), args=tuple(tuple(args) for args in case["args"])
        )
    return FunctionInput(dict(case["input"]))


def _requires_expected(case_input: CaseInput, comparator: ComparatorSpec) -> bool:
    has_no_expected = isinstance(case_input, GeneratedInput | StressScenario)
    return not has_no_expected and comparator.type is not ComparatorType.CHECKER


def _reject_duplicate_ids(items: Sequence[Document], location: str, label: str) -> None:
    seen: set[str] = set()
    for index, item in enumerate(items):
        identifier = item["id"]
        if identifier in seen:
            raise _DocumentError(f"{location}[{index}].id", f'duplicate {label} "{identifier}"')
        seen.add(identifier)
