import json
from collections.abc import Callable
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from coding_study.adapters.schema_validation import (
    MAX_MESSAGE_LENGTH,
    META_SCHEMA_FILE,
    TESTS_SCHEMA_FILE,
    SchemaValidator,
)
from tests.helpers import (
    BANK_PROJECT,
    PROJECT_PROBLEMS,
    PROJECT_STRESS_PROBLEMS,
    SCHEMAS_DIRECTORY,
    TALLY_PROJECT,
    load_fixture_meta,
    load_fixture_tests,
)

SOURCE = "problems/0001-two-sum/meta.yaml"

type Mutation = Callable[[dict[str, Any]], None]


def validator_for_meta_file() -> SchemaValidator:
    return SchemaValidator.from_file(SCHEMAS_DIRECTORY / META_SCHEMA_FILE)


def validator_for_tests_file() -> SchemaValidator:
    return SchemaValidator.from_file(SCHEMAS_DIRECTORY / TESTS_SCHEMA_FILE)


def locations_after(validator: SchemaValidator, document: dict[str, Any], mutate: Mutation):
    mutate(document)
    return [issue.location for issue in validator.violations(document, SOURCE)]


@pytest.mark.parametrize("schema_file", [META_SCHEMA_FILE, TESTS_SCHEMA_FILE])
def test_schema_is_valid_draft_2020_12(schema_file):
    Draft202012Validator.check_schema(json.loads((SCHEMAS_DIRECTORY / schema_file).read_text()))


@pytest.mark.parametrize("directory_name", ["0001-two-sum", "0002-lru-cache"])
def test_fixture_meta_is_valid(directory_name):
    assert validator_for_meta_file().violations(load_fixture_meta(directory_name), SOURCE) == []


@pytest.mark.parametrize(
    "languages",
    [["python"], ["rust", "python"], ["go", "rust"], ["python", "typescript", "java", "kotlin"]],
    ids=["one", "any order", "go and rust alone", "the core four"],
)
def test_a_problem_may_list_any_subset_of_the_languages(languages):
    meta = load_fixture_meta("0001-two-sum")
    meta["languages"] = languages
    assert validator_for_meta_file().violations(meta, SOURCE) == []


@pytest.mark.parametrize(
    "jdk",
    [{"min": 24}, {"max": 23}, {"min": 22, "max": 25}, {"max": 27}],
    ids=["minimum only", "maximum only", "both", "a maximum above the supported range"],
)
def test_a_problem_may_declare_the_jdk_range_it_runs_on(jdk):
    meta = load_fixture_meta("0001-two-sum")
    meta["jdk"] = jdk
    assert validator_for_meta_file().violations(meta, SOURCE) == []


def test_a_problem_lists_at_least_one_language():
    meta = load_fixture_meta("0001-two-sum")
    meta["languages"] = []
    issues = validator_for_meta_file().violations(meta, SOURCE)
    assert [issue.location for issue in issues] == ["languages"]


@pytest.mark.parametrize("directory_name", ["0001-two-sum", "0002-lru-cache"])
def test_fixture_tests_are_valid(directory_name):
    assert validator_for_tests_file().violations(load_fixture_tests(directory_name), SOURCE) == []


def set_function_param(name: str, value: Any) -> Mutation:
    def mutate(meta: dict[str, Any]) -> None:
        meta["signature"]["function"]["params"][0][name] = value

    return mutate


def set_returns(**values: Any) -> Mutation:
    def mutate(meta: dict[str, Any]) -> None:
        meta["signature"]["function"]["returns"].update(values)

    return mutate


INVALID_META: dict[str, tuple[Mutation, str]] = {
    "missing slug": (lambda meta: meta.pop("slug"), ""),
    "id not 4 digits": (lambda meta: meta.update(id="1"), "id"),
    "unknown status": (lambda meta: meta.update(status="done"), "status"),
    "unknown top-level key": (lambda meta: meta.update(hints=["think"]), ""),
    "dsa without patterns": (lambda meta: meta.pop("patterns"), ""),
    "unknown pattern": (lambda meta: meta.update(patterns=["sorting"]), "patterns[0]"),
    "approach languages not a language": (
        lambda meta: meta["approaches"][0].update(languages=["scala"]),
        "approaches[0].languages[0]",
    ),
    "unknown language": (
        lambda meta: meta.update(languages=["python", "typescript", "java", "kotlin", "scala"]),
        "languages[4]",
    ),
    "jdk without bounds": (lambda meta: meta.update(jdk={}), "jdk"),
    "jdk that is not an object": (lambda meta: meta.update(jdk=24), "jdk"),
    "unknown jdk key": (lambda meta: meta.update(jdk={"min": 24, "preview": True}), "jdk"),
    "jdk minimum that is a string": (lambda meta: meta.update(jdk={"min": "24"}), "jdk.min"),
    "jdk maximum that is not whole": (lambda meta: meta.update(jdk={"max": 24.5}), "jdk.max"),
    "levels on a function problem": (
        lambda meta: meta.update(levels=[{"level": 1, "title": "Basics"}]),
        "",
    ),
    "class signature on a function problem": (
        lambda meta: meta.update(signature={"class": meta["signature"].pop("function")}),
        "signature",
    ),
    "function and class signatures": (
        lambda meta: meta["signature"].update({"class": {}}),
        "signature",
    ),
    "snake_case param name": (
        set_function_param("name", "max_value"),
        "signature.function.params[0].name",
    ),
    "non-string param type": (set_function_param("type", 5), "signature.function.params[0].type"),
    "index return without of": (set_returns(**{"as": "index"}), "signature.function.returns"),
    "unknown return modifier": (set_returns(copy=True), "signature.function.returns"),
    "per_method on exact comparator": (
        lambda meta: meta.update(comparator={"type": "exact", "per_method": {"get": "float"}}),
        "comparator.type",
    ),
    "unknown comparator": (
        lambda meta: meta.update(comparator={"type": "fuzzy"}),
        "comparator.type",
    ),
    "no optimal approach": (
        lambda meta: meta["approaches"][1].update(role="intermediate"),
        "approaches",
    ),
    "two oracles": (lambda meta: meta["approaches"][1].update(oracle=True), "approaches"),
    "unknown complexity class": (
        lambda meta: meta["approaches"][0].update(time_class="n^4"),
        "approaches[0].time_class",
    ),
    "time limit with factor and ms": (
        lambda meta: meta["perf"].update(time_limit={"factor": 5, "ms": 100}),
        "perf.time_limit",
    ),
}


@pytest.mark.parametrize(("mutate", "location"), INVALID_META.values(), ids=list(INVALID_META))
def test_invalid_meta_is_reported_at_its_location(mutate, location):
    assert location in locations_after(
        validator_for_meta_file(), load_fixture_meta("0001-two-sum"), mutate
    )


def project_meta() -> dict[str, Any]:
    return load_fixture_meta(BANK_PROJECT, PROJECT_PROBLEMS)


def test_project_fixture_meta_is_valid():
    assert validator_for_meta_file().violations(project_meta(), SOURCE) == []


def test_the_project_block_may_name_the_tests_directory():
    meta = project_meta()
    meta["project"]["tests"] = "checks/levels"
    assert validator_for_meta_file().violations(meta, SOURCE) == []


INVALID_PROJECT_META: dict[str, tuple[Mutation, str]] = {
    "no project block": (lambda meta: meta.pop("project"), ""),
    "no languages": (lambda meta: meta.pop("languages"), ""),
    "two languages": (lambda meta: meta.update(languages=["python", "typescript"]), "languages"),
    "no levels": (lambda meta: meta.pop("levels"), ""),
    "no entry": (lambda meta: meta["project"].pop("entry"), "project"),
    "empty entry": (lambda meta: meta["project"].update(entry=""), "project.entry"),
    "empty tests directory": (lambda meta: meta["project"].update(tests=""), "project.tests"),
    "unknown project key": (lambda meta: meta["project"].update(starter="src"), "project"),
    "stub": (lambda meta: meta.update(stub="generated"), ""),
    "perf": (lambda meta: meta.update(perf={"budget_ms": 100}), ""),
}


@pytest.mark.parametrize(
    ("mutate", "location"), INVALID_PROJECT_META.values(), ids=list(INVALID_PROJECT_META)
)
def test_invalid_project_meta_is_reported_at_its_location(mutate, location):
    assert location in locations_after(validator_for_meta_file(), project_meta(), mutate)


@pytest.mark.parametrize("directory_name", ["0001-two-sum", "0002-lru-cache"])
def test_only_a_project_problem_has_a_project_block(directory_name):
    def add_project(meta: dict[str, Any]) -> None:
        meta["project"] = {"entry": "bank.bank"}

    meta = load_fixture_meta(directory_name)
    assert "" in locations_after(validator_for_meta_file(), meta, add_project)


def first_method_is(**values: Any) -> Mutation:
    def mutate(meta: dict[str, Any]) -> None:
        meta["signature"]["class"]["methods"][0].update(values)

    return mutate


def test_a_project_method_may_be_async():
    meta = project_meta()
    first_method_is(**{"async": True})(meta)
    assert validator_for_meta_file().violations(meta, SOURCE) == []


def test_a_project_may_declare_the_virtual_clock():
    meta = project_meta()
    meta["project"]["clock"] = "virtual"
    assert validator_for_meta_file().violations(meta, SOURCE) == []


def stress_project_meta() -> dict[str, Any]:
    return load_fixture_meta(TALLY_PROJECT, PROJECT_STRESS_PROBLEMS)


def test_a_project_may_have_a_concurrency_block():
    assert validator_for_meta_file().violations(stress_project_meta(), SOURCE) == []


def test_a_project_names_one_concurrency_model():
    meta = stress_project_meta()
    meta["concurrency"]["model"] = {"python": "threads"}
    assert "concurrency.model" in [
        issue.location for issue in validator_for_meta_file().violations(meta, SOURCE)
    ]


@pytest.mark.parametrize("directory_name", ["0001-two-sum", "0002-lru-cache"])
def test_only_concurrent_and_project_problems_have_a_concurrency_block(directory_name):
    def add_concurrency(meta: dict[str, Any]) -> None:
        meta["concurrency"] = {"model": "threads"}

    meta = load_fixture_meta(directory_name)
    assert "" in locations_after(validator_for_meta_file(), meta, add_concurrency)


def test_a_project_stress_case_has_a_level():
    tests = load_fixture_tests(TALLY_PROJECT, PROJECT_STRESS_PROBLEMS)
    assert validator_for_tests_file().violations(tests, SOURCE) == []


INVALID_CLOCK_META: dict[str, tuple[Mutation, str]] = {
    "async that is not a boolean": (
        first_method_is(**{"async": "yes"}),
        "signature.class.methods[0].async",
    ),
    "the real clock written out": (
        lambda meta: meta["project"].update(clock="real"),
        "project.clock",
    ),
    "a clock that is a boolean": (lambda meta: meta["project"].update(clock=True), "project.clock"),
    "an empty clock": (lambda meta: meta["project"].update(clock=""), "project.clock"),
}


@pytest.mark.parametrize(
    ("mutate", "location"), INVALID_CLOCK_META.values(), ids=list(INVALID_CLOCK_META)
)
def test_an_invalid_clock_declaration_is_reported_at_its_location(mutate, location):
    assert location in locations_after(validator_for_meta_file(), project_meta(), mutate)


def first_case(**values: Any) -> Mutation:
    def mutate(tests: dict[str, Any]) -> None:
        tests["cases"][0].update(values)

    return mutate


def generated_case(**values: Any) -> Mutation:
    def mutate(tests: dict[str, Any]) -> None:
        tests["cases"][3].update(values)

    return mutate


INVALID_TESTS: dict[str, tuple[Mutation, str]] = {
    "unsupported version": (lambda tests: tests.update(version=2), "version"),
    "missing cases": (lambda tests: tests.pop("cases"), ""),
    "uppercase case id": (first_case(id="Ex1"), "cases[0].id"),
    "no input, ops or generate": (lambda tests: tests["cases"][0].pop("input"), "cases[0]"),
    "input and generate": (first_case(generate={"n": 10, "seed": 1}), "cases[0]"),
    "ops without args": (first_case(ops=["LRUCache"]), "cases[0]"),
    "generated case with expected": (generated_case(expected=[0, 1]), "cases[3]"),
    "visible generated case": (generated_case(visible=True), "cases[3].visible"),
    "non-integer seed": (
        generated_case(generate={"n": 10, "seed": "one"}),
        "cases[3].generate.seed",
    ),
}


@pytest.mark.parametrize(("mutate", "location"), INVALID_TESTS.values(), ids=list(INVALID_TESTS))
def test_invalid_tests_are_reported_at_their_location(mutate, location):
    assert location in locations_after(
        validator_for_tests_file(), load_fixture_tests("0001-two-sum"), mutate
    )


def project_tests() -> dict[str, Any]:
    return json.loads((PROJECT_PROBLEMS / BANK_PROJECT / "tests.json").read_text())


def first_project_case_runs(*operations: str) -> Mutation:
    """The first case with its operations after the constructor replaced by `operations`."""

    def mutate(tests: dict[str, Any]) -> None:
        case = tests["cases"][0]
        case["ops"] = [case["ops"][0], *operations]
        case["args"] = [case["args"][0], *([[]] * len(operations))]
        case["expected"] = [None] * len(case["ops"])

    return mutate


@pytest.mark.parametrize(
    "operations",
    [
        ["@advance"],
        ["@spawn", "@join", "@now"],
        ["createAccount", "@advance", "@now"],
    ],
    ids=["one", "all but the method", "mixed with a method"],
)
def test_a_case_may_hold_the_harness_operations(operations):
    tests = project_tests()
    first_project_case_runs(*operations)(tests)
    assert validator_for_tests_file().violations(tests, SOURCE) == []


@pytest.mark.parametrize(
    "operation",
    ["@", "@Advance", "@1", "@now now", "@advance!", "advance@", "@@now", " @now"],
)
def test_an_operation_that_is_neither_a_method_nor_a_harness_operation_is_refused(operation):
    tests = project_tests()
    first_project_case_runs(operation)(tests)
    assert "cases[0].ops[1]" in [
        issue.location for issue in validator_for_tests_file().violations(tests, SOURCE)
    ]


def test_a_stress_scenario_keeps_its_setup_to_methods():
    scenario = {
        "setup": {"ops": ["@now"], "args": [[]]},
        "workers": [{"group": "w", "count": 2, "repeat": 1, "steps": [{"op": "put", "args": []}]}],
        "final": {"ops": ["size"], "args": [[]], "expected": [0]},
    }
    tests = {"version": 1, "cases": [{"id": "s1", "stress": scenario}]}
    locations = [issue.location for issue in validator_for_tests_file().violations(tests, SOURCE)]
    assert locations == ["cases[0].stress.setup.ops[0]"]


def test_reports_every_violation_not_just_the_first():
    meta = load_fixture_meta("0001-two-sum")
    meta.update(status="done", difficulty="trivial")
    assert len(validator_for_meta_file().violations(meta, SOURCE)) == 2


def test_violation_names_the_file_and_the_problem():
    meta = load_fixture_meta("0001-two-sum")
    meta.update(status="done")
    [issue] = validator_for_meta_file().violations(meta, SOURCE)
    assert str(issue) == f"{SOURCE}: status: 'done' is not one of ['draft', 'ready']"


def test_long_messages_are_truncated():
    hidden_case = {
        "id": "h9",
        "input": {"nums": list(range(500))},
        "generate": {"n": 10, "seed": 1},
    }
    tests = {"version": 1, "cases": [hidden_case]}
    [issue] = validator_for_tests_file().violations(tests, SOURCE)
    assert len(issue.message) == MAX_MESSAGE_LENGTH


def test_a_schema_is_checked_once_however_many_validators_read_it(monkeypatch):
    """`cstudy serve` loads a problem with a fresh environment on every request, so its
    validators are new each time; the check of the schema costs tens of milliseconds."""
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "checked once"}
    checks: list[object] = []
    monkeypatch.setattr(Draft202012Validator, "check_schema", checks.append)
    for _ in range(3):
        SchemaValidator(schema).violations({}, SOURCE)
    assert len(checks) == 1


def test_a_changed_schema_is_checked_again(monkeypatch):
    checks: list[object] = []
    monkeypatch.setattr(Draft202012Validator, "check_schema", checks.append)
    for title in ("first", "second"):
        SchemaValidator({"title": f"changed {title}"}).violations({}, SOURCE)
    assert len(checks) == 2
