"""What `cstudy history` reads from progress.db (docs/specs/cli.md#cstudy-history)."""

from datetime import UTC, datetime, timedelta

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt, RunRecord
from coding_study.domain.bench_records import BenchRunRecord, BenchRunSummary
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language

STARTED = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
LATER = STARTED + timedelta(hours=1)


@pytest.fixture
def store(tmp_path) -> SqliteProgressStore:
    return SqliteProgressStore(tmp_path / "progress.db")


def start(store: SqliteProgressStore, slug: str, language: Language | None, at: datetime) -> int:
    return store.add_attempt(NewAttempt(slug, language, AttemptMode.NEW, at)).id


def bench(attempt_id: int | None, ran_at: datetime, verdict: Verdict) -> BenchRunRecord:
    return BenchRunRecord(
        attempt_id=attempt_id,
        slug="two-sum",
        language=Language.PYTHON,
        ran_at=ran_at,
        code_hash="abc",
        sizes=(100,),
        series=(),
        verdict=verdict,
        confidence=Confidence.HIGH,
        reference_id="hash-map",
        ratio=1.1,
    )


def test_attempts_of_a_slug_come_in_every_language_latest_first(store):
    python = start(store, "two-sum", Language.PYTHON, STARTED)
    kotlin = start(store, "two-sum", Language.KOTLIN, LATER)
    assert [attempt.id for attempt in store.attempts("two-sum")] == [kotlin, python]


def test_attempts_of_another_slug_are_left_out(store):
    start(store, "lru-cache", Language.PYTHON, STARTED)
    assert store.attempts("two-sum") == ()


def test_attempts_of_an_item_have_no_language(store):
    start(store, "url-shortener", None, STARTED)
    assert store.attempts("url-shortener")[0].language is None


def test_test_runs_of_an_attempt_come_earliest_first(store):
    attempt_id = start(store, "two-sum", Language.PYTHON, STARTED)
    later = RunRecord(attempt_id, LATER, "b", Tally(total=4, passed=4), 20, "5x")
    earlier = RunRecord(attempt_id, STARTED, "a", Tally(total=4, passed=3, failed=1), 10)
    store.add_test_run(later)
    store.add_test_run(earlier)
    assert store.test_runs(attempt_id) == (earlier, later)


def test_test_runs_of_another_attempt_are_left_out(store):
    attempt_id = start(store, "two-sum", Language.PYTHON, STARTED)
    other = start(store, "two-sum", Language.KOTLIN, STARTED)
    store.add_test_run(RunRecord(other, STARTED, "a", Tally(total=4), 10))
    assert store.test_runs(attempt_id) == ()


def test_bench_runs_of_an_attempt_come_earliest_first(store):
    attempt_id = start(store, "two-sum", Language.PYTHON, STARTED)
    store.add_bench_run(bench(attempt_id, LATER, Verdict.OPTIMAL))
    store.add_bench_run(bench(attempt_id, STARTED, Verdict.SUBOPTIMAL))
    assert store.bench_runs(attempt_id) == (
        BenchRunSummary(STARTED, Verdict.SUBOPTIMAL, Confidence.HIGH, 1.1, "hash-map"),
        BenchRunSummary(LATER, Verdict.OPTIMAL, Confidence.HIGH, 1.1, "hash-map"),
    )


def test_reference_only_bench_runs_belong_to_no_attempt(store):
    attempt_id = start(store, "two-sum", Language.PYTHON, STARTED)
    store.add_bench_run(bench(None, STARTED, Verdict.OPTIMAL))
    assert store.bench_runs(attempt_id) == ()
