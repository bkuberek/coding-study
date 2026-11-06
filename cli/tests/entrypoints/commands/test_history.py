"""`cstudy history` output and JSON document (docs/specs/cli.md#cstudy-history)."""

import json
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import (
    AttemptMode,
    AttemptStatus,
    Grade,
    NewAttempt,
    Rating,
    RunRecord,
)
from coding_study.domain.bench_records import BenchRunRecord
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import history
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
WEEK_AGO = NOW - timedelta(days=7)
REVIEWED = NOW - timedelta(hours=1)


@pytest.fixture
def environment(tmp_path, monkeypatch) -> Environment:
    environment = make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))
    monkeypatch.setattr(history, "load_environment", lambda *_: environment)
    return environment


def cs_history(*arguments: str):
    return runner.invoke(cli.app, ["history", *arguments])


def lines(*arguments: str) -> list[str]:
    return cs_history(*arguments).output.splitlines()


def document(*arguments: str):
    return json.loads(cs_history(*arguments, "--json").stdout)


def local(instant: datetime) -> str:
    return instant.astimezone().strftime("%Y-%m-%d %H:%M")


def schedule(environment: Environment, due_on: date) -> None:
    state = ReviewState(ease=2.5, interval_days=7, reps=2, lapses=0)
    environment.progress.save_schedule_entry(ScheduleEntry("two-sum", state, due_on, Grade.OK, NOW))


def attempt(environment: Environment, language: Language, mode: AttemptMode, at: datetime) -> int:
    return environment.progress.add_attempt(NewAttempt("two-sum", language, mode, at)).id


def finish(environment: Environment, attempt_id: int, **fields: object) -> None:
    found = next(
        found for found in environment.progress.attempts("two-sum") if found.id == attempt_id
    )
    environment.progress.update_attempt(replace(found, **fields))  # type: ignore[arg-type]


def run(environment: Environment, attempt_id: int, passed: int = 4) -> RunRecord:
    record = RunRecord(attempt_id, NOW, "abc", Tally(total=4, passed=passed, failed=4 - passed), 10)
    environment.progress.add_test_run(record)
    return record


def bench(environment: Environment, attempt_id: int, verdict: Verdict) -> None:
    environment.progress.add_bench_run(
        BenchRunRecord(
            attempt_id=attempt_id,
            slug="two-sum",
            language=Language.PYTHON,
            ran_at=NOW,
            code_hash="abc",
            sizes=(100,),
            series=(),
            verdict=verdict,
            confidence=Confidence.MEDIUM,
            reference_id="hash-map",
            ratio=1.3,
        )
    )


def three_attempts(environment: Environment) -> None:
    """An abandoned and a failed attempt in Python, then a passed review in Kotlin."""
    abandoned = attempt(environment, Language.PYTHON, AttemptMode.NEW, WEEK_AGO)
    finish(environment, abandoned, status=AttemptStatus.ABANDONED, ended_at=WEEK_AGO)
    run(environment, abandoned, passed=0)
    failed_at = WEEK_AGO + timedelta(minutes=31)
    failed = attempt(environment, Language.PYTHON, AttemptMode.NEW, failed_at)
    finish(
        environment,
        failed,
        status=AttemptStatus.FAILED,
        ended_at=failed_at + timedelta(minutes=41, seconds=2),
        grade=Grade.AGAIN,
        hints_used=2,
        solution_revealed=True,
    )
    run(environment, failed, passed=3)
    run(environment, failed, passed=3)
    passed = attempt(environment, Language.KOTLIN, AttemptMode.REVIEW, REVIEWED)
    finish(
        environment,
        passed,
        status=AttemptStatus.PASSED,
        ended_at=REVIEWED + timedelta(minutes=18, seconds=40),
        rating=Rating.OK,
        grade=Grade.OK,
    )
    for _ in range(3):
        run(environment, passed)
    bench(environment, passed, Verdict.OPTIMAL)


def test_a_problem_without_attempts_says_so(environment):
    assert lines("two-sum") == [
        "two-sum · easy · arrays-hashing · new",
        "review     not scheduled",
        "",
        "no attempts yet",
    ]


def test_history_exits_0(environment):
    assert cs_history("two-sum").exit_code == ExitCode.SUCCESS


def test_an_unknown_slug_exits_3(environment):
    assert cs_history("three-sum").exit_code == ExitCode.USAGE_ERROR


def test_an_items_header_names_its_track(environment):
    assert lines("url-shortener")[0] == "url-shortener · medium · system-design · new"


@pytest.mark.parametrize(
    ("days", "when"),
    [(3, "in 3 days"), (1, "in 1 day"), (0, "today"), (-1, "1 day ago"), (-2, "2 days ago")],
)
def test_the_review_line_says_how_far_off_the_due_date_is(environment, days, when):
    due_on = NOW.date() + timedelta(days=days)
    schedule(environment, due_on)
    assert lines("two-sum")[1] == (
        f"review     due {due_on.isoformat()} ({when}) · interval 7d · ease 2.50 · reps 2 · "
        "lapses 0"
    )


def test_attempts_are_listed_newest_first(environment):
    three_attempts(environment)
    assert lines("two-sum")[3:] == [
        "ATTEMPT  LANG    MODE    STATUS     STARTED           TIME     RATING  GRADE           "
        "HINTS  TESTS  BENCH",
        f"3        kotlin  review  passed     {local(REVIEWED)}  18m 40s  ok      ok              "
        "0      3      optimal",
        f"2        python  new     failed     {local(WEEK_AGO + timedelta(minutes=31))}  41m 02s  "
        "-       again solution  2      2      -",
        f"1        python  new     abandoned  {local(WEEK_AGO)}  -        -       -               "
        "0      1      -",
    ]


def test_an_attempt_in_progress_has_no_time(environment):
    attempt(environment, Language.PYTHON, AttemptMode.NEW, NOW)
    assert lines("two-sum")[4].split()[3:7] == ["in_progress", *local(NOW).split(), "-"]


def test_the_header_reads_in_progress_in_words_and_the_json_keeps_the_value(environment):
    attempt(environment, Language.PYTHON, AttemptMode.NEW, NOW)
    assert lines("two-sum")[0] == "two-sum · easy · arrays-hashing · in progress"
    assert document("two-sum")["status"] == "in_progress"


def test_json_describes_the_problem(environment):
    schedule(environment, date(2026, 10, 27))
    found = document("two-sum")
    assert {key: found[key] for key in ("slug", "kind", "track", "status", "schedule")} == {
        "slug": "two-sum",
        "kind": "function",
        "track": "dsa",
        "status": "new",
        "schedule": {
            "due_on": "2026-10-27",
            "interval_days": 7,
            "ease": 2.5,
            "reps": 2,
            "lapses": 0,
            "last_grade": "ok",
        },
    }


def test_json_without_a_schedule_has_none(environment):
    assert document("two-sum")["schedule"] is None


def test_json_describes_each_attempt_with_its_runs(environment):
    started = attempt(environment, Language.PYTHON, AttemptMode.NEW, NOW)
    ended = NOW + timedelta(minutes=41, seconds=2)
    finish(
        environment,
        started,
        status=AttemptStatus.FAILED,
        ended_at=ended,
        grade=Grade.AGAIN,
        hints_used=2,
        solution_revealed=True,
    )
    run(environment, started, passed=3)
    bench(environment, started, Verdict.SUBOPTIMAL)
    assert document("two-sum")["attempts"] == [
        {
            "attempt_id": started,
            "language": "python",
            "mode": "new",
            "status": "failed",
            "started_at": NOW.isoformat(),
            "ended_at": ended.isoformat(),
            "solve_s": 2462,
            "rating": None,
            "grade": "again",
            "hints_used": 2,
            "solution_revealed": True,
            "time_limit_s": None,
            "level_unlocked": None,
            "levels_finished": None,
            "test_runs": [
                {
                    "ran_at": NOW.isoformat(),
                    "total": 4,
                    "passed": 3,
                    "failed": 1,
                    "errored": 0,
                    "timed_out": 0,
                    "tle": 0,
                    "time_limit": None,
                    "duration_ms": 10,
                }
            ],
            "submissions": [],
            "bench_runs": [
                {
                    "ran_at": NOW.isoformat(),
                    "verdict": "suboptimal",
                    "confidence": "medium",
                    "ratio": 1.3,
                    "reference_id": "hash-map",
                }
            ],
        }
    ]


def test_json_lists_the_attempts_newest_first(environment):
    three_attempts(environment)
    assert [found["attempt_id"] for found in document("two-sum")["attempts"]] == [3, 2, 1]


def test_json_gives_an_abandoned_attempt_no_solve_time(environment):
    three_attempts(environment)
    assert document("two-sum")["attempts"][2]["solve_s"] is None


def test_json_of_an_item_has_no_language(environment):
    environment.progress.add_attempt(NewAttempt("url-shortener", None, AttemptMode.NEW, NOW))
    found = document("url-shortener")
    assert (found["kind"], found["attempts"][0]["language"]) == ("item", None)


# project problems


@pytest.fixture
def project(tmp_path, monkeypatch) -> Environment:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    monkeypatch.setattr(history, "load_environment", lambda *_: environment)
    return environment


def submit(environment: Environment) -> None:
    environment.progress.add_submission(
        SubmissionRecord(
            attempt_id=1,
            submitted_at=NOW,
            code_hash="abc",
            graded_up_to=1,
            every_level=True,
            levels=(LevelTally(1, 1, 1, 2, 2),),
            tally=Tally(total=3, passed=3),
            duration_ms=300,
        )
    )


def test_a_project_counts_its_submissions_as_tests(project):
    submit(project)
    assert lines(PROJECT_SLUG)[4].split()[-2:] == ["1", "-"]


def test_json_lists_a_projects_submissions_and_levels_finished(project):
    submit(project)
    found = document(PROJECT_SLUG)["attempts"][0]
    assert (found["levels_finished"], found["submissions"]) == (
        1,
        [
            {
                "submitted_at": NOW.isoformat(),
                "graded_up_to": 1,
                "every_level": True,
                "levels": [
                    {
                        "level": 1,
                        "total": 3,
                        "passed": 3,
                        "visible_total": 1,
                        "visible_passed": 1,
                        "hidden_total": 2,
                        "hidden_passed": 2,
                    }
                ],
                "total": 3,
                "passed": 3,
                "duration_ms": 300,
            }
        ],
    )
