from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptStatus, Grade, Rating, RunRecord
from coding_study.domain.bench_records import BenchRunRecord
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.config import Config, ScheduleSettings
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState
from tests.fakes import NOW, FakeClock, FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
SOLVE_TIME = timedelta(minutes=18, seconds=40)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def environment(tmp_path: Path, clock: FakeClock):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(root, toolchains=toolchains, clock=clock)
    start_attempt(environment, StartRequest("two-sum"))
    clock.advance(SOLVE_TIME)
    return environment


def record_run(environment, passed: int, total: int = 4) -> None:
    attempt = environment.progress.active_attempt()
    tally = Tally(total=total, passed=passed, failed=total - passed)
    environment.progress.add_test_run(RunRecord(attempt.id, NOW, "hash", tally, 10))
    if passed == total:
        environment.progress.update_attempt(replace(attempt, first_pass_at=NOW))


def record_bench(environment, verdict: Verdict, confidence: Confidence, ran_at=NOW) -> None:
    attempt = environment.progress.active_attempt()
    run = BenchRunRecord(
        attempt.id, "two-sum", Language.PYTHON, ran_at, "hash", (100,), (), verdict, confidence
    )
    environment.progress.add_bench_run(run)


def done(environment, **fields):
    return complete_attempt(environment, DoneRequest(**fields))


def test_a_full_pass_with_a_rating_passes_the_attempt(environment):
    record_run(environment, passed=4)
    assert done(environment, rating=Rating.OK).attempt.status is AttemptStatus.PASSED


def test_rating_sets_the_grade(environment):
    record_run(environment, passed=4)
    assert done(environment, rating=Rating.EASY).attempt.grade is Grade.EASY


def test_finishing_records_the_end_and_notes(environment):
    record_run(environment, passed=4)
    attempt = done(environment, rating=Rating.OK, notes="used a map").attempt
    assert (attempt.ended_at, attempt.notes) == (NOW + SOLVE_TIME, "used a map")


def test_finishing_closes_the_attempt(environment):
    record_run(environment, passed=4)
    done(environment, rating=Rating.OK)
    assert environment.progress.active_attempt() is None


def test_giving_up_fails_the_attempt_with_grade_again(environment):
    record_run(environment, passed=1)
    attempt = done(environment, gave_up=True).attempt
    assert (attempt.status, attempt.grade) == (AttemptStatus.FAILED, Grade.AGAIN)


def test_giving_up_without_any_run(environment):
    assert done(environment, gave_up=True).attempt.status is AttemptStatus.FAILED


def test_schedules_the_first_review(environment):
    record_run(environment, passed=4)
    entry = done(environment, rating=Rating.OK).schedule
    assert (entry.state, entry.due_on) == (ReviewState(2.5, 3, 1, 0), date(2026, 10, 27))


def test_schedule_is_stored(environment):
    record_run(environment, passed=4)
    entry = done(environment, rating=Rating.OK).schedule
    assert environment.progress.schedule_entry("two-sum") == entry


def test_later_reviews_build_on_the_previous_schedule(environment, clock):
    record_run(environment, passed=4)
    done(environment, rating=Rating.OK)
    start_attempt(environment, StartRequest("two-sum"))
    record_run(environment, passed=4)
    assert done(environment, rating=Rating.OK).schedule.state.interval_days == 7


def test_rating_after_a_failing_run_is_a_usage_error(environment):
    record_run(environment, passed=2)
    with pytest.raises(UsageError, match="--gave-up"):
        done(environment, rating=Rating.OK)


def test_rating_after_a_partial_run_is_a_usage_error(environment):
    record_run(environment, passed=1, total=1)
    with pytest.raises(UsageError, match="--gave-up"):
        done(environment, rating=Rating.OK)


def test_giving_up_after_a_full_pass_is_a_usage_error(environment):
    record_run(environment, passed=4)
    with pytest.raises(UsageError, match="--rating"):
        done(environment, gave_up=True)


@pytest.mark.parametrize("fields", [{}, {"rating": Rating.OK, "gave_up": True}])
def test_exactly_one_of_rating_and_gave_up(environment, fields):
    with pytest.raises(UsageError, match="either"):
        done(environment, **fields)


def test_no_attempt_in_progress(environment):
    with pytest.raises(UsageError, match="no attempt in progress"):
        done(environment, slug="lru-cache", gave_up=True)


@pytest.mark.parametrize("confidence", [Confidence.MEDIUM, Confidence.HIGH])
def test_a_confident_suboptimal_bench_caps_the_grade_at_hard(environment, confidence):
    record_run(environment, passed=4)
    record_bench(environment, Verdict.SUBOPTIMAL, confidence)
    assert done(environment, rating=Rating.EASY).attempt.grade is Grade.HARD


def test_a_low_confidence_suboptimal_bench_leaves_the_grade(environment):
    record_run(environment, passed=4)
    record_bench(environment, Verdict.SUBOPTIMAL, Confidence.LOW)
    assert done(environment, rating=Rating.EASY).attempt.grade is Grade.EASY


def test_only_the_latest_bench_counts(environment):
    record_run(environment, passed=4)
    record_bench(environment, Verdict.SUBOPTIMAL, Confidence.HIGH)
    record_bench(environment, Verdict.OPTIMAL, Confidence.HIGH, ran_at=NOW + timedelta(minutes=5))
    assert done(environment, rating=Rating.EASY).attempt.grade is Grade.EASY


def test_the_suboptimal_penalty_can_be_turned_off(environment):
    record_run(environment, passed=4)
    record_bench(environment, Verdict.SUBOPTIMAL, Confidence.HIGH)
    config = Config(schedule=ScheduleSettings(penalize_suboptimal=False))
    finished = complete_attempt(
        replace(environment, config=config), DoneRequest(rating=Rating.EASY)
    )
    assert finished.attempt.grade is Grade.EASY
