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
from coding_study.adapters.http_grader.case_document import http_case_input
from coding_study.domain.cases import (
    Case,
    CaseInput,
    Expected,
    FunctionInput,
    GeneratedInput,
    OperationSequence,
)
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.jdk import DeclaredJdk
from coding_study.domain.labels import Labels
from coding_study.domain.problem import (
    ALL_LANGUAGES,
    CORE_LANGUAGES,
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
from coding_study.domain.project import DEFAULT_TESTS_DIRECTORY, NO_ENTRY, Project
from coding_study.domain.sandbox import DEFAULT_READY_S
from coding_study.domain.service_project import (
    ServiceApp,
    ServiceCommands,
    ServiceMock,
    ServiceProject,
    ServiceRequires,
    ServiceSizes,
    ServiceTimeouts,
)
from coding_study.domain.signature import (
    NO_SIGNATURE,
    ClassSignature,
    FunctionSignature,
    Method,
    NodeSerialization,
    Param,
    Returns,
    Signature,
    async_issues,
    blocking_issues,
    modifier_issues,
)
from coding_study.domain.stress import StressScenario
from coding_study.domain.taxonomy import Scope
from coding_study.domain.time_limits import AbsoluteTimeLimit, FactorTimeLimit, TimeLimit
from coding_study.domain.type_dsl import TypeSyntaxError, parse_return_type, parse_value_type
from coding_study.domain.virtual_clock import ProjectClock, clock_declaration_issues

type Document = Mapping[str, Any]


class _DocumentError(Exception):
    def __init__(self, location: str, message: str) -> None:
        super().__init__(message)
        self.location = location
        self.message = message


def labels_from_document(document: Document) -> Labels:
    """The `domains`, `job_roles` and `scope` of a `meta.yaml` or `item.yaml` document."""
    scope = document.get("scope")
    return Labels(
        domains=tuple(document.get("domains", ())),
        job_roles=tuple(document.get("job_roles", ())),
        scope=Scope(scope) if scope is not None else None,
    )


def meta_from_document(document: Document, source: str, workspace: bool = False) -> ProblemMeta:
    """`source` is the repository-relative file name used in reported issues. A `workspace`
    problem is the user's own: without a `languages` line it lists the core languages."""
    try:
        meta = _meta(document, workspace)
    except _DocumentError as issue:
        raise ContentError([ContentIssue(source, issue.location, issue.message)]) from None
    issues = modifier_issues(meta.signature)
    if meta.kind is not ProblemKind.CONCURRENT:
        issues += blocking_issues(meta.signature)
    if meta.kind is ProblemKind.PROJECT:
        issues += clock_declaration_issues(meta)
    else:
        issues += async_issues(meta.signature)
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


def _meta(document: Document, workspace: bool) -> ProblemMeta:
    default = CORE_LANGUAGES if workspace else ALL_LANGUAGES
    languages = tuple(Language(name) for name in document.get("languages", default))
    concurrency = document.get("concurrency")
    return ProblemMeta(
        id=document["id"],
        slug=document["slug"],
        title=document["title"],
        status=ContentStatus(document["status"]),
        difficulty=Difficulty(document["difficulty"]),
        track=Track(document["track"]),
        kind=ProblemKind(document["kind"]),
        signature=_signature(document["signature"]) if "signature" in document else NO_SIGNATURE,
        comparator=_comparator(document["comparator"]),
        approaches=_approaches(document["approaches"]),
        patterns=tuple(document.get("patterns", ())),
        labels=labels_from_document(document),
        languages=languages,
        jdk=_jdk(document.get("jdk")),
        stub=StubSource(document.get("stub", StubSource.GENERATED)),
        levels=tuple(Level(level["level"], level["title"]) for level in document.get("levels", ())),
        perf=_perf(document.get("perf", {})),
        hang_guard_ms=document.get("limits", {}).get("hang_guard_ms"),
        references=_references(document.get("references", {})),
        related=tuple(document.get("related", ())),
        order=document.get("order", DEFAULT_CURRICULUM_ORDER),
        estimate_minutes=document.get("estimate_minutes"),
        summary=document.get("summary"),
        concurrency=(
            concurrency_from_document(concurrency, languages) if concurrency is not None else None
        ),
        project=_project(document.get("project")),
        workspace=workspace,
    )


def _jdk(jdk: Document | None) -> DeclaredJdk | None:
    if jdk is None:
        return None
    return DeclaredJdk(minimum=jdk.get("min"), maximum=jdk.get("max"))


def _project(project: Document | None) -> Project | None:
    if project is None:
        return None
    clock = project.get("clock")
    return Project(
        entry=project.get("entry", NO_ENTRY),
        tests=project.get("tests", DEFAULT_TESTS_DIRECTORY),
        clock=ProjectClock(clock) if clock is not None else None,
        service=_service(project) if "grading" in project else None,
    )


def _service(project: Document) -> ServiceProject:
    app = project["app"]
    requires = project.get("requires", {})
    sizes = requires.get("sizes", {})
    timeouts = project.get("timeouts_s", {})
    defaults = ServiceTimeouts()
    return ServiceProject(
        image=project["image"],
        commands=_service_commands(project["commands"]),
        app=ServiceApp(
            port_env=app["port_env"],
            port=app["port"],
            health=app["health"],
            ready_timeout_s=app.get("ready_timeout_s", DEFAULT_READY_S),
            mem_limit=app.get("mem_limit"),
        ),
        env=dict(project.get("env", {})),
        requires=ServiceRequires(
            lock=requires.get("lock"),
            services=tuple(requires.get("services", ())),
            sizes=ServiceSizes(
                install_mb=sizes.get("install_mb"),
                images_mb=dict(sizes.get("images_mb", {})),
                memory_mb=sizes.get("memory_mb"),
            ),
        ),
        mocks=tuple(ServiceMock(mock["name"], mock["config"]) for mock in project.get("mocks", ())),
        services=project.get("services"),
        install_env=dict(project.get("install_env", {})),
        timeouts=ServiceTimeouts(
            startup=timeouts.get("startup", defaults.startup),
            install=timeouts.get("install", defaults.install),
            test=timeouts.get("test", defaults.test),
            reset=timeouts.get("reset", defaults.reset),
        ),
    )


def _service_commands(commands: Document) -> ServiceCommands:
    def optional(name: str) -> tuple[str, ...] | None:
        return tuple(commands[name]) if name in commands else None

    return ServiceCommands(
        run=tuple(commands["run"]),
        test=tuple(commands["test"]),
        install=optional("install"),
        bootstrap=optional("bootstrap"),
        reset=optional("reset"),
        grade_setup=optional("grade_setup"),
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
        is_async=method.get("async", False),
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
    if "request" in case:
        return http_case_input(case)
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
