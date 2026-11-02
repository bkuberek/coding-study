"""`cstudy submit` on a project with stress cases (docs/specs/cli.md#cstudy-submit): the stress
cases of the graded levels run after their cases, and each (stress case, variant) counts as one
hidden case of its level."""

from dataclasses import replace

import pytest

from coding_study.application.environment import Environment
from coding_study.application.project_events import stream_submission
from coding_study.application.run_events import (
    CaseGraded,
    LevelGraded,
    RunEvent,
    StressGraded,
    StressRunJudged,
    StressRunStarted,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest, SubmitResult, submit_project
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.concurrency import ConcurrencyModel
from coding_study.domain.problem import Problem
from coding_study.domain.runs import UserError
from coding_study.domain.submissions import LevelTally
from tests.project_fakes import (
    TALLY_SLUG,
    ScriptedProjectProcess,
    stress_project_environment,
    tally_answers,
)

STRESS_RUNS = 3
"""`concurrency.runs` of the fixture."""
SYNTAX_ERROR = UserError("SyntaxError", "invalid syntax", "tally/tally.py:3")


@pytest.fixture
def process() -> ScriptedProjectProcess:
    return ScriptedProjectProcess()


@pytest.fixture
def environment(tmp_path, process) -> Environment:
    environment = stress_project_environment(tmp_path, process)
    process.answer = tally_answers(problem_of(environment))
    start_attempt(environment, StartRequest(TALLY_SLUG))
    return environment


def problem_of(environment: Environment) -> Problem:
    return environment.problems.load(TALLY_SLUG)


def submit(environment: Environment) -> SubmitResult:
    return submit_project(environment, SubmitRequest(), [].append)


@pytest.fixture
def at_level_2(environment) -> Environment:
    """Level 1 passed, so level 2 and its stress cases are open."""
    assert submit(environment).opened is not None
    return environment


def test_a_level_without_stress_cases_runs_none(environment, process):
    submit(environment)
    (job,) = process.gradings
    assert (job.model, [case.id for case in job.cases][-1]) == (None, "h4")


def test_the_stress_cases_of_the_open_levels_run_after_their_cases(at_level_2, process):
    submit(at_level_2)
    job = process.gradings[-1]
    stress = [case.id for case in job.cases if ":" in case.id]
    assert stress == [
        *(f"s1:thread:{run}" for run in range(STRESS_RUNS)),
        *(f"s2:thread:{run}" for run in range(STRESS_RUNS)),
    ]
    assert job.model is ConcurrencyModel.THREADS


def test_each_stress_verdict_counts_as_a_hidden_case_of_its_level(at_level_2):
    result = submit(at_level_2)
    assert result.level_tallies == (LevelTally(1, 2, 2, 4, 4), LevelTally(2, 2, 2, 6, 6))
    assert (result.submission.tally.total, result.submission.tally.passed) == (14, 14)


def test_a_failing_stress_case_fails_its_level(at_level_2, process):
    process.answer = tally_answers(problem_of(at_level_2), racy=True)
    result = submit(at_level_2)
    assert result.level_tallies[1] == LevelTally(2, 2, 2, 6, 5)
    statuses = {verdict.case_id: verdict.status for verdict in result.judgement.stress}
    assert statuses == {"s1": CaseStatus.FAIL, "s2": CaseStatus.PASS}


def test_a_full_pass_with_stress_cases_is_the_full_pass(at_level_2):
    result = submit(at_level_2)
    assert result.finished_every_level


def test_code_that_does_not_load_fails_every_stress_case_too(at_level_2, process):
    process.load_error = SYNTAX_ERROR
    result = submit(at_level_2)
    assert result.level_tallies[1] == LevelTally(2, 2, 0, 6, 0)
    assert result.submission.tally.errored == 14


# --events


def stream(environment: Environment) -> list[RunEvent]:
    events: list[RunEvent] = []
    stream_submission(environment, SubmitRequest(), events.append)
    return events


def test_each_stress_run_is_reported_with_its_level(at_level_2):
    events = stream(at_level_2)
    started = [event for event in events if isinstance(event, StressRunStarted)]
    judged = [event for event in events if isinstance(event, StressRunJudged)]
    assert [(event.planned.run_id, event.level) for event in started][:2] == [
        ("s1:thread:0", 2),
        ("s1:thread:1", 2),
    ]
    assert {event.level for event in judged} == {2}
    assert len(judged) == 2 * STRESS_RUNS


def test_each_stress_case_and_variant_is_graded_right_after_its_last_run(at_level_2):
    events = stream(at_level_2)
    graded = [event for event in events if isinstance(event, StressGraded)]
    assert [(event.verdict.case_id, event.level) for event in graded] == [("s1", 2), ("s2", 2)]
    before = events[events.index(graded[0]) - 1]
    assert isinstance(before, StressRunJudged)
    assert before.planned.run_id == f"s1:thread:{STRESS_RUNS - 1}"


def test_stress_results_come_after_the_cases_and_before_the_levels(at_level_2):
    events = stream(at_level_2)
    kinds = [type(event) for event in events]
    last_case = max(i for i, kind in enumerate(kinds) if kind is CaseGraded)
    first_stress = kinds.index(StressRunStarted)
    last_stress = max(i for i, kind in enumerate(kinds) if kind is StressGraded)
    assert last_case < first_stress < last_stress < kinds.index(LevelGraded)


def test_a_mock_attempt_names_no_stress_case(tmp_path, process):
    environment = stress_project_environment(tmp_path, process)
    process.answer = tally_answers(problem_of(environment))
    start_attempt(environment, StartRequest(TALLY_SLUG, mock=True))
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    environment.progress.update_attempt(replace(attempt, level_unlocked=2))
    events = stream(environment)
    stress = (StressRunStarted, StressRunJudged, StressGraded)
    assert [event for event in events if isinstance(event, stress)] == []
    tallies = [event.tally for event in events if isinstance(event, LevelGraded)]
    assert tallies[1] == LevelTally(2, 2, 2, 6, 6)
