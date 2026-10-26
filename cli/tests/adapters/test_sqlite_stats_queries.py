"""The progress.db queries behind `cstudy stats`."""

from datetime import UTC, datetime, timedelta

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.bench_records import BenchRunRecord
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.problem import Language
from coding_study.domain.progress_stats import LatestBench

RAN_AT = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path):
    return SqliteProgressStore(tmp_path / "progress.db")


@pytest.fixture
def attempt_id(store):
    started = NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, RAN_AT)
    return store.add_attempt(started).id


def bench_run(attempt_id: int | None, verdict: Verdict, **overrides: object) -> BenchRunRecord:
    fields: dict[str, object] = {
        "attempt_id": attempt_id,
        "slug": "two-sum",
        "language": Language.PYTHON,
        "ran_at": RAN_AT,
        "code_hash": "abc",
        "sizes": (100,),
        "series": (),
        "verdict": verdict,
        "confidence": Confidence.MEDIUM,
    }
    return BenchRunRecord(**(fields | overrides))  # type: ignore[arg-type]


def test_latest_bench_verdicts_keep_the_latest_run(store, attempt_id):
    store.add_bench_run(bench_run(attempt_id, Verdict.SUBOPTIMAL))
    later = RAN_AT + timedelta(hours=1)
    store.add_bench_run(bench_run(attempt_id, Verdict.OPTIMAL, ran_at=later))
    assert store.latest_bench_verdicts() == (
        LatestBench("two-sum", Language.PYTHON, Verdict.OPTIMAL, later),
    )


def test_latest_bench_verdicts_are_per_language(store, attempt_id):
    store.add_bench_run(bench_run(attempt_id, Verdict.OPTIMAL))
    store.add_bench_run(bench_run(attempt_id, Verdict.UNKNOWN, language=Language.JAVA))
    languages = [found.language for found in store.latest_bench_verdicts()]
    assert languages == [Language.JAVA, Language.PYTHON]


def test_latest_bench_verdicts_skip_reference_only_runs(store, attempt_id):
    store.add_bench_run(bench_run(attempt_id, Verdict.OPTIMAL))
    store.add_bench_run(bench_run(None, Verdict.UNKNOWN, ran_at=RAN_AT + timedelta(hours=1)))
    assert [found.verdict for found in store.latest_bench_verdicts()] == [Verdict.OPTIMAL]


def test_latest_bench_verdicts_break_ties_by_the_later_row(store, attempt_id):
    store.add_bench_run(bench_run(attempt_id, Verdict.SUBOPTIMAL))
    store.add_bench_run(bench_run(attempt_id, Verdict.NEAR_OPTIMAL))
    assert [found.verdict for found in store.latest_bench_verdicts()] == [Verdict.NEAR_OPTIMAL]
