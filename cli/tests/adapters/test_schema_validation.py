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
from tests.helpers import SCHEMAS_DIRECTORY, load_fixture_meta, load_fixture_tests

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
