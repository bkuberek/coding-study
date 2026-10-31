import json
import shutil
from pathlib import Path

import pytest

from coding_study.adapters.conformance_fixtures import (
    CONFORMANCE_DIRECTORY,
    conformance_repository,
    load_conformance_suite,
)
from coding_study.domain.cases import OperationSequence
from coding_study.domain.conformance import (
    ConformanceExpectation,
    ExpectedOutcome,
    ExpectedStatus,
    ExpectedTestStatus,
)
from coding_study.domain.errors import ContentError
from coding_study.domain.signature import ClassSignature
from tests.helpers import MAPPING_TABLE_TYPES, REPOSITORY_ROOT, SCHEMAS_DIRECTORY

DEEPEST_LIST = "list<list<list<int>>>"
SUITE = load_conformance_suite(REPOSITORY_ROOT)
REPOSITORY = conformance_repository(REPOSITORY_ROOT)
SUMMARIES = REPOSITORY.list_summaries()


def write_expectations(root: Path, document: object) -> None:
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas")
    directory = root / CONFORMANCE_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "expectations.json").write_text(json.dumps(document))


def echoed_arguments(case_input: object) -> list[object]:
    """null for the constructor and the void method, else each operation's argument."""
    assert isinstance(case_input, OperationSequence)
    operations = zip(case_input.ops[1:], case_input.args[1:], strict=True)
    return [None, *(None if op == "noop" else args[0] for op, args in operations)]


def test_suite_reads_the_conformance_directory():
    assert SUITE.problems_directory == "runners/conformance"


def test_every_fixture_loads_with_its_cases():
    assert all(REPOSITORY.load(summary.meta.slug).cases for summary in SUMMARIES)


def test_every_fixture_has_an_expectation():
    expected_slugs = {expectation.slug for expectation in SUITE.expectations}
    assert {summary.meta.slug for summary in SUMMARIES} == expected_slugs


@pytest.mark.parametrize("expectation", SUITE.expectations, ids=lambda e: e.approach_id)
def test_expectations_name_declared_approaches(expectation):
    meta = REPOSITORY.load(expectation.slug).meta
    assert expectation.approach_id in {approach.id for approach in meta.approaches}


@pytest.mark.parametrize("expectation", SUITE.expectations, ids=lambda e: e.approach_id)
def test_case_overrides_name_existing_cases(expectation):
    case_ids = {case.id for case in REPOSITORY.load(expectation.slug).cases}
    assert set(expectation.case_outcomes) <= case_ids


TYPE_FIXTURES = ("conformance-types", "conformance-decimal-date-types")
"""Echo every DSL type; `decimal` and `date` have a fixture of their own, so a runner can join
the suite before it supports them."""


def test_type_fixtures_cover_every_type_in_the_mapping_table():
    declared: set[str] = set()
    for slug in TYPE_FIXTURES:
        signature = REPOSITORY.load(slug).meta.signature
        assert isinstance(signature, ClassSignature)
        declared |= {str(param.type) for method in signature.methods for param in method.params}
    assert declared == {*MAPPING_TABLE_TYPES, DEEPEST_LIST}


def test_the_types_fixture_leaves_decimal_and_date_to_their_own_fixture():
    signature = REPOSITORY.load("conformance-types").meta.signature
    assert isinstance(signature, ClassSignature)
    declared = " ".join(str(param.type) for method in signature.methods for param in method.params)
    assert ("decimal" in declared, "date" in declared) == (False, False)


@pytest.mark.parametrize("slug", TYPE_FIXTURES)
def test_type_fixtures_expect_every_argument_back(slug):
    mismatches = [
        case.id
        for case in REPOSITORY.load(slug).cases
        if case.expected is None or case.expected.value != echoed_arguments(case.input)
    ]
    assert mismatches == []


def test_case_override_wins_over_the_default():
    timeout = ExpectedOutcome(ExpectedStatus.TIMEOUT)
    expectation = ConformanceExpectation(
        "s", "a", ExpectedOutcome(ExpectedStatus.PASS), {"c": timeout}
    )
    assert expectation.outcome_for("c").status is ExpectedStatus.TIMEOUT


def test_cases_without_override_use_the_default():
    expectation = ConformanceExpectation("s", "a", ExpectedOutcome(ExpectedStatus.PASS), {})
    assert expectation.outcome_for("c").status is ExpectedStatus.PASS


def test_parses_error_details():
    [op_error] = [e for e in SUITE.expectations if e.slug == "conformance-op-error"]
    assert op_error.outcome_for("fails") == ExpectedOutcome(
        ExpectedStatus.ERROR, message="counter failure", op_index=3, partial_output=(None, 1, 2)
    )


def test_parses_expected_stdout():
    [stdout] = [e for e in SUITE.expectations if e.slug == "conformance-stdout"]
    assert stdout.outcome.stdout == "conformance output\n"


def suite_expectation() -> ConformanceExpectation:
    [suite] = [e for e in SUITE.expectations if e.slug == "conformance-suite-pytest"]
    return suite


def test_parses_the_expected_outcome_of_each_test_of_a_suite():
    statuses = {test_id: test.status for test_id, test in suite_expectation().tests.items()}
    assert statuses == {
        "tests/test_level_1.py::test_ex1": ExpectedTestStatus.OK,
        "tests/test_statuses.py::test_passes": ExpectedTestStatus.OK,
        "tests/test_statuses.py::test_hangs": ExpectedTestStatus.TIMEOUT,
        "tests/test_statuses.py::test_fails_an_assertion": ExpectedTestStatus.FAILED,
        "tests/test_statuses.py::test_ends_the_process": ExpectedTestStatus.CRASHED,
        "tests/test_statuses.py::test_raises": ExpectedTestStatus.ERROR,
        "tests/test_statuses.py::test_prints": ExpectedTestStatus.OK,
    }


def test_parses_a_tests_message_and_output():
    tests = suite_expectation().tests
    raises, prints = (
        tests[f"tests/test_statuses.py::{name}"] for name in ("test_raises", "test_prints")
    )
    assert (raises.message, prints.stdout) == ("conformance failure", "conformance output\n")


def test_a_grading_fixture_expects_no_tests():
    [grading] = [e for e in SUITE.expectations if e.slug == "conformance-project-python"]
    assert grading.tests == {}


def test_a_node_test_suite_expects_the_same_statuses_under_its_own_test_ids():
    [suite] = [e for e in SUITE.expectations if e.slug == "conformance-suite-node-test"]
    statuses = {test_id: test.status for test_id, test in suite.tests.items()}
    assert statuses == {
        "tests/level-1.test.ts::ex1": ExpectedTestStatus.OK,
        "tests/statuses.test.ts::passes": ExpectedTestStatus.OK,
        "tests/statuses.test.ts::hangs": ExpectedTestStatus.TIMEOUT,
        "tests/statuses.test.ts::fails an assertion": ExpectedTestStatus.FAILED,
        "tests/statuses.test.ts::ends the process": ExpectedTestStatus.CRASHED,
        "tests/statuses.test.ts::raises": ExpectedTestStatus.ERROR,
        "tests/statuses.test.ts::prints": ExpectedTestStatus.OK,
    }


@pytest.mark.parametrize(("language", "extension"), [("java", "java"), ("kotlin", "kt")])
def test_a_junit_suite_expects_what_only_the_junit_platform_reports(language, extension):
    """A class whose setup fails is one result under its file's id; a disabled test and a failed
    assumption are skipped; a parameterized test is one result per invocation."""
    [suite] = [e for e in SUITE.expectations if e.slug == f"conformance-suite-junit-{language}"]
    statuses = {test_id: test.status for test_id, test in suite.tests.items()}
    tests = f"src/test/{language}/probe"
    assert {
        test_id: statuses[test_id]
        for test_id in (
            f"{tests}/BrokenSetupTest.{extension}",
            f"{tests}/StatusesTest.{extension}::disabled",
            f"{tests}/StatusesTest.{extension}::assumes",
            f"{tests}/StatusesTest.{extension}::counts[2]",
        )
    } == {
        f"{tests}/BrokenSetupTest.{extension}": ExpectedTestStatus.ERROR,
        f"{tests}/StatusesTest.{extension}::disabled": ExpectedTestStatus.SKIPPED,
        f"{tests}/StatusesTest.{extension}::assumes": ExpectedTestStatus.SKIPPED,
        f"{tests}/StatusesTest.{extension}::counts[2]": ExpectedTestStatus.OK,
    }


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"version": 2, "expectations": []}, "version"),
        ({"version": 1}, "expectations"),
        ({"version": 1, "expectations": [{"problem": "p", "approach": "a"}]}, "outcome"),
        (
            {"version": 1, "expectations": [{"problem": "p", "approach": "a", "outcome": {}}]},
            "status",
        ),
        (
            {
                "version": 1,
                "expectations": [
                    {
                        "problem": "p",
                        "approach": "a",
                        "outcome": {"status": "pass"},
                        "tests": {"t": {"status": "pass"}},
                    }
                ],
            },
            "tests",
        ),
    ],
)
def test_malformed_expectations_are_content_errors(tmp_path, document, message):
    write_expectations(tmp_path, document)
    with pytest.raises(ContentError, match=message):
        load_conformance_suite(tmp_path)


def test_missing_expectations_file_is_a_content_error(tmp_path):
    with pytest.raises(ContentError, match="file not found"):
        load_conformance_suite(tmp_path)
