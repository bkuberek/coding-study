"""A project's grading job with stress cases (docs/specs/runners.md#stress-in-project-jobs): the
sequential cases of the graded levels, then each planned stress run, judged per (stress case,
variant) as a concurrent problem's are."""

from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.application.environment import Environment
from coding_study.application.ports import ProjectGrading
from coding_study.application.project_runs import GradingRun, grading_stress_plan, run_grading
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.concurrency import ConcurrencyModel, StressVariant
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.problem import Language, Problem
from coding_study.domain.stress_runs import PlannedRun, StressSelection
from coding_study.domain.stress_verdict import StressRunResult
from tests.project_fakes import (
    TALLY_SLUG,
    FakeProjectRunner,
    ScriptedProjectProcess,
    project_toolchains,
    stress_project_environment,
    tally_answers,
)

ROOT = Path("/ws/projects/tally")
SEQUENTIAL_CASES = 12
STRESS_RUNS = 3
"""`concurrency.runs` of the fixture."""


@dataclass
class Heard:
    events: list[str] = field(default_factory=list[str])

    def case_started(self, case: RunnableCase) -> None:
        self.events.append(f"start {case.id}")

    def case_judged(self, verdict: CaseVerdict) -> None:
        self.events.append(f"judged {verdict.case.id}")

    def stress_run_started(self, planned: PlannedRun) -> None:
        self.events.append(f"start {planned.run_id}")

    def stress_run_judged(self, planned: PlannedRun, result: StressRunResult) -> None:
        self.events.append(f"judged {planned.run_id} {result.status}")


@pytest.fixture
def runner() -> FakeProjectRunner:
    return FakeProjectRunner()


@pytest.fixture
def environment(tmp_path, runner) -> Environment:
    toolchains = project_toolchains(PythonTestGenerator(), runner)
    return stress_project_environment(tmp_path, ScriptedProjectProcess(), toolchains=toolchains)


@pytest.fixture
def problem(environment) -> Problem:
    return environment.problems.load(TALLY_SLUG)


def graded(
    environment: Environment, problem: Problem, level: int = 2, *, racy: bool = False, **run: object
):
    process = ScriptedProjectProcess(answer=tally_answers(problem, racy=racy))
    plan = grading_stress_plan(problem, Language.PYTHON, level, StressSelection())
    grading = GradingRun(problem, Language.PYTHON, ROOT, level, stress_plan=plan, **run)  # type: ignore[arg-type]
    judgement = run_grading(replace(environment, runner_process=process), grading, [].append)
    (job,) = process.gradings
    return judgement, job


def test_the_stress_cases_of_the_graded_levels_are_planned(problem):
    plan = grading_stress_plan(problem, Language.PYTHON, 2, StressSelection())
    assert [planned.run_id for planned in plan] == [
        *(f"s1:thread:{run}" for run in range(STRESS_RUNS)),
        *(f"s2:thread:{run}" for run in range(STRESS_RUNS)),
    ]


def test_a_level_below_the_stress_cases_plans_none(problem):
    assert grading_stress_plan(problem, Language.PYTHON, 1, StressSelection()) == ()


def test_a_selection_sets_the_runs(problem):
    plan = grading_stress_plan(problem, Language.PYTHON, 2, StressSelection(runs=10))
    assert len(plan) == 20


def test_the_job_carries_the_cases_then_each_stress_run(environment, problem):
    _, job = graded(environment, problem)
    ids = [case.id for case in job.cases]
    assert ids[:SEQUENTIAL_CASES] == [case.id for case in problem.cases][:SEQUENTIAL_CASES]
    assert ids[SEQUENTIAL_CASES:] == [
        *(f"s1:thread:{run}" for run in range(STRESS_RUNS)),
        *(f"s2:thread:{run}" for run in range(STRESS_RUNS)),
    ]


def test_a_job_with_stress_runs_names_the_concurrency_model(environment, problem):
    _, job = graded(environment, problem)
    assert job.model is ConcurrencyModel.THREADS


def test_a_job_without_a_stress_plan_leaves_the_stress_cases_out(environment, problem):
    process = ScriptedProjectProcess(answer=tally_answers(problem))
    grading = GradingRun(problem, Language.PYTHON, ROOT, 2)
    judgement = run_grading(replace(environment, runner_process=process), grading, [].append)
    (job,) = process.gradings
    assert (len(job.cases), job.model, judgement.stress) == (SEQUENTIAL_CASES, None, ())


def test_each_stress_case_and_variant_is_one_verdict(environment, problem):
    judgement, _ = graded(environment, problem)
    verdicts = [
        (verdict.case_id, verdict.variant, len(verdict.runs)) for verdict in judgement.stress
    ]
    assert verdicts == [
        ("s1", StressVariant.THREAD, STRESS_RUNS),
        ("s2", StressVariant.THREAD, STRESS_RUNS),
    ]
    assert (judgement.passed, judgement.case_count) == (True, SEQUENTIAL_CASES + 2)


def test_a_stress_run_that_breaks_an_invariant_fails_its_case(environment, problem):
    judgement, _ = graded(environment, problem, racy=True)
    statuses = {verdict.case_id: verdict.status for verdict in judgement.stress}
    assert statuses == {"s1": CaseStatus.FAIL, "s2": CaseStatus.PASS}
    assert not judgement.passed


def test_the_listener_hears_each_stress_run(environment, problem):
    heard = Heard()
    graded(environment, problem, listener=heard)
    assert heard.events[-2:] == ["start s2:thread:2", "judged s2:thread:2 PASS"]
    assert "judged s1:thread:0 PASS" in heard.events


def test_the_runner_shares_the_class_from_the_level_of_the_first_stress_case(
    environment, problem, runner
):
    graded(environment, problem, level=1)
    graded(environment, problem, level=2)
    shared = [scope.shared for scope in runner.scopes if isinstance(scope, ProjectGrading)]
    assert shared == [False, True]
