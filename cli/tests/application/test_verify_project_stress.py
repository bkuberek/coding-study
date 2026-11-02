"""`cstudy verify` D6 and D7 on a project with stress cases (docs/specs/authoring.md#dynamic): the
reference passes every stress case in 10 of 10 runs, and each broken overlay, built on the starter
and the reference's overlay, passes every sequential case and fails each of its `caught_by` stress
cases in at least 9 of 10."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.verify_content import (
    ProblemVerification,
    VerifyRequest,
    verify_content,
)
from coding_study.application.verify_projects import PROJECT_BUILDS
from coding_study.domain.problem import Problem
from coding_study.domain.runs import CaseOutcome, Returned, RunCase, RunJob, StressCompleted
from coding_study.domain.stress_runs import RUN_ID_SEPARATOR
from tests.fakes import make_environment, repository_root
from tests.helpers import PROJECT_STRESS_PROBLEMS
from tests.project_fakes import (
    LEVEL_1_TEST,
    TALLY_SLUG,
    FakeTestGenerator,
    ScriptedBuilds,
    ScriptedProjectProcess,
    project_toolchains,
    raises_not_implemented,
    tally_answers,
)

BROKEN_FOLDER = "broken-unlocked-add"
BROKEN_BUILD = f"{PROJECT_BUILDS}/{TALLY_SLUG}/{BROKEN_FOLDER}"
VERIFY_RUNS = 10
FEW_RUNS = 3
DEADLINE_NS = 5_000_000_000


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return repository_root(tmp_path, PROJECT_STRESS_PROBLEMS)


@pytest.fixture
def problem(root: Path) -> Problem:
    return make_environment(root).problems.load(TALLY_SLUG)


@pytest.fixture
def builds(problem: Problem) -> ScriptedBuilds:
    tests = (LEVEL_1_TEST,)
    return ScriptedBuilds(
        starter=ScriptedProjectProcess(tests, raises_not_implemented),
        reference=ScriptedProjectProcess(tests, tally_answers(problem)),
        broken={BROKEN_FOLDER: ScriptedProjectProcess(tests, tally_answers(problem, racy=True))},
    )


@pytest.fixture
def environment(root: Path, builds: ScriptedBuilds) -> Environment:
    toolchains = project_toolchains(FakeTestGenerator())
    return make_environment(root, toolchains=toolchains, runner_process=builds)


def verify(environment: Environment, **fields: object) -> ProblemVerification:
    """With 3 runs per stress case, unless `stress_runs` says otherwise: judging is quick."""
    defaults = {"slugs": (TALLY_SLUG,), "stress_runs": FEW_RUNS}
    request = VerifyRequest(**(defaults | fields))  # type: ignore[arg-type]
    [verified] = verify_content(environment, request, lambda _line: None).problems
    return verified


def stress_ids(job: RunJob) -> list[str]:
    return [case.id for case in job.cases if RUN_ID_SEPARATOR in case.id]


def test_a_reference_that_passes_its_stress_cases_and_a_caught_broken_overlay_pass(environment):
    verified = verify(environment)
    (result,) = verified.languages
    assert (verified.passed, result.passed) == (True, True)
    assert [(check.target_id, check.verdict.case_id, check.ok) for check in result.stress] == [
        ("reference", "s1", True),
        ("reference", "s2", True),
        ("unlocked-add", "s1", True),
    ]


def test_the_reference_runs_every_stress_case_10_times(environment, builds):
    verify(environment, stress_runs=None)
    graded = builds.reference.gradings[0]
    assert [run.rpartition(RUN_ID_SEPARATOR)[0] for run in stress_ids(graded)] == [
        *["s1:thread"] * VERIFY_RUNS,
        *["s2:thread"] * VERIFY_RUNS,
    ]


def test_stress_n_sets_the_runs(environment, builds):
    verify(environment, stress_runs=4)
    assert len(stress_ids(builds.reference.gradings[0])) == 8


def test_a_broken_overlay_runs_only_the_stress_cases_that_catch_it(environment, builds):
    verify(environment)
    (graded,) = builds.broken[BROKEN_FOLDER].gradings
    assert stress_ids(graded) == [f"s1:thread:{run}" for run in range(FEW_RUNS)]


def test_a_broken_overlay_builds_over_the_reference(environment, root):
    verify(environment)
    build = root / BROKEN_BUILD
    assert "without the lock" in (build / "tally" / "counts.py").read_text()
    assert "from tally.counts import Counts" in (build / "tally" / "tally.py").read_text()


def test_a_broken_overlay_that_is_not_caught_fails_d7(environment, builds, problem):
    builds.broken[BROKEN_FOLDER].answer = tally_answers(problem)
    verified = verify(environment)
    (result,) = verified.languages
    assert not verified.passed
    assert result.broken[0].failures == ("s1 thread caught in 0/3 runs (needs 3)",)


def test_a_broken_overlay_must_pass_the_sequential_cases(environment, builds, problem):
    racy = tally_answers(problem, racy=True)

    def wrong_on_h1(job: RunJob, case: RunCase) -> CaseOutcome:
        return Returned(-1, 1_000) if case.id == "h1" else racy(job, case)

    builds.broken[BROKEN_FOLDER].answer = wrong_on_h1
    (result,) = verify(environment).languages
    assert result.broken[0].failures[0].startswith("sequential level 1 h1 FAIL")


def test_a_reference_that_fails_a_stress_case_fails_d6(environment, builds, problem):
    builds.reference.answer = tally_answers(problem, racy=True)
    (result,) = verify(environment).languages
    (reference,) = result.approaches
    assert reference.failures[0].startswith("s1 thread 0/3 runs passed; run 0 seed 1000: ")


def test_ready_needs_the_slowest_correct_run_within_a_quarter_of_its_deadline(
    environment, builds, problem
):
    answer = tally_answers(problem)

    def slow(job: RunJob, case: RunCase) -> CaseOutcome:
        outcome = answer(job, case)
        if isinstance(outcome, StressCompleted):
            return replace(outcome, duration_ns=DEADLINE_NS * 2 // 5)
        return outcome

    builds.reference.answer = slow
    verified = verify(environment, require_ready=True)
    assert (
        "the slowest correct stress run (python reference s1 thread) uses 40% of its deadline; "
        "at most 25%"
    ) in verified.ready_errors


def test_the_starter_runs_no_stress(environment, builds):
    verify(environment)
    assert [stress_ids(job) for job in builds.starter.gradings] == [[]]
