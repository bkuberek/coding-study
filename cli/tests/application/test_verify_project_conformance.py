"""`cstudy verify --conformance` on the project fixtures: a reference's build is graded at its
last level, and a suite fixture's native suite runs with an expected outcome per test
(docs/specs/runners.md#conformance-suite)."""

import json
import shutil
from pathlib import Path

import pytest

from coding_study.adapters.conformance_fixtures import (
    conformance_repository,
    load_conformance_suite,
)
from coding_study.adapters.environment_factory import conformance_environment
from coding_study.application.environment import Environment
from coding_study.application.verify_conformance import (
    ConformanceRequest,
    FixtureVerification,
    verify_conformance,
)
from coding_study.application.verify_projects import PROJECT_BUILDS
from coding_study.domain.problem import Language
from coding_study.domain.runs import Crashed, ProjectTarget, Raised, Returned, TimedOut, UserError
from coding_study.domain.suite_runs import AssertionFailed, Passed, SuiteTest
from tests.fakes import make_environment
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.project_fakes import (
    FakeTestGenerator,
    ScriptedBuilds,
    project_toolchains,
    scripted_builds,
)

CONFORMANCE = REPOSITORY_ROOT / "runners" / "conformance"
FIXTURES = ("9022-conformance-project-python", "9024-conformance-suite-pytest")
GRADING, SUITE = "conformance-project-python", "conformance-suite-pytest"
STATUSES = "tests/test_statuses.py"
FAILURE = "assert 'pong' == 'ping'"
EXPECTED_TESTS = (
    SuiteTest("tests/test_level_1.py::test_ex1", Passed(1_000)),
    SuiteTest(f"{STATUSES}::test_passes", Passed(1_000)),
    SuiteTest(f"{STATUSES}::test_hangs", TimedOut(1_000)),
    SuiteTest(f"{STATUSES}::test_fails_an_assertion", AssertionFailed(FAILURE, 1_000)),
    SuiteTest(f"{STATUSES}::test_ends_the_process", Crashed(3)),
    SuiteTest(
        f"{STATUSES}::test_raises",
        Raised(UserError("RuntimeError", "conformance failure"), 1_000),
    ),
    SuiteTest(f"{STATUSES}::test_prints", Passed(1_000, "conformance output\n")),
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    (tmp_path / "problems").mkdir()
    fixtures = tmp_path / "runners" / "conformance"
    for directory in FIXTURES:
        shutil.copytree(CONFORMANCE / directory, fixtures / directory)
    expectations = json.loads((CONFORMANCE / "expectations.json").read_text())
    expectations["expectations"] = [
        entry for entry in expectations["expectations"] if entry["problem"] in (GRADING, SUITE)
    ]
    (fixtures / "expectations.json").write_text(json.dumps(expectations))
    return tmp_path


@pytest.fixture
def process(root: Path) -> ScriptedBuilds:
    fixtures = conformance_repository(root)
    process = scripted_builds(*(fixtures.load(slug) for slug in (GRADING, SUITE)))
    process.reference.tests = EXPECTED_TESTS
    return process


@pytest.fixture
def environment(root: Path, process: ScriptedBuilds) -> Environment:
    toolchains = project_toolchains(FakeTestGenerator())
    return conformance_environment(
        make_environment(root, toolchains=toolchains, runner_process=process)
    )


def conformance(environment: Environment, slug: str) -> FixtureVerification:
    request = ConformanceRequest((slug,), Language.PYTHON)
    suite = load_conformance_suite(environment.root)
    [result] = verify_conformance(environment, suite, request, lambda _: None)
    return result


def failures(result: FixtureVerification) -> tuple[str, ...]:
    [language] = result.languages
    return (*language.problems, *(f for approach in language.approaches for f in approach.failures))


def test_a_project_fixture_passes_when_its_cases_pass(environment, process):
    assert conformance(environment, GRADING).passed


def test_a_project_fixture_is_graded_in_its_references_build(environment, process):
    conformance(environment, GRADING)
    [request] = process.reference.requests
    [job] = request.jobs
    assert job.target == ProjectTarget(
        str(environment.root / PROJECT_BUILDS / GRADING / "reference"), "store.inventory"
    )


def test_a_grading_fixture_runs_no_suite(environment, process):
    conformance(environment, GRADING)
    assert [*process.starter.suites, *process.reference.suites] == []


def test_a_project_fixture_has_no_generated_stub_to_check(environment, process):
    conformance(environment, GRADING)
    assert (len(process.starter.requests), len(process.reference.requests)) == (0, 1)


def test_a_case_with_another_outcome_fails_the_fixture(environment, process):
    process.reference.answer = lambda job, case: Returned([None, 1, 1, "pens: 1"], 1_000)
    assert failures(conformance(environment, GRADING)) == (
        "ex1: expected pass, got FAIL",
        "h1: expected pass, got FAIL",
    )


def test_a_reference_that_does_not_load_fails_the_fixture(environment, process):
    process.reference.load_error = UserError("SymbolNotFound", "no class Inventory")
    assert failures(conformance(environment, GRADING)) == (
        "unexpected load_error: SymbolNotFound: no class Inventory",
    )


def test_a_suite_fixture_passes_when_each_test_has_its_outcome(environment, process):
    assert conformance(environment, SUITE).passed


def test_a_suite_fixture_runs_every_levels_tests(environment, process):
    conformance(environment, SUITE)
    [job] = process.reference.suites
    assert job.exclude == ()


def test_a_test_with_another_outcome_fails_the_suite_fixture(environment, process):
    tests = tuple(
        SuiteTest(test.test_id, Passed(1_000)) if test.test_id.endswith("test_raises") else test
        for test in EXPECTED_TESTS
    )
    process.reference.tests = tests
    assert failures(conformance(environment, SUITE)) == (
        f"{STATUSES}::test_raises: expected error, got ok",
    )


def test_a_missing_overlay_is_a_missing_reference(environment, process, root):
    shutil.rmtree(root / "runners" / "conformance" / FIXTURES[0] / "solutions" / "reference")
    assert failures(conformance(environment, GRADING)) == ("no python reference for reference",)
