import json
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from importlib import resources

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.bench_records import BenchOutcome, BenchRunRecord
from coding_study.domain.bench_runs import USER_TARGET_ID
from coding_study.domain.bench_stats import SizeStats, SizeStatus, TargetSeries
from coding_study.domain.bench_verdict import Confidence, PastRun, Verdict
from coding_study.domain.problem import Language

RAN_AT = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
USER = TargetSeries(
    USER_TARGET_ID,
    (
        SizeStats(100, SizeStatus.COMPLETED, 900.0, 0.02, 800.0, 50, 7064, "tracemalloc_peak"),
        SizeStats(1000, SizeStatus.BUDGET_EXCEEDED, exceeded_ns=5_000_000_000),
    ),
)
REFERENCE = TargetSeries(
    "hash-map", (SizeStats(100, SizeStatus.COMPLETED, 700.0, 0.01, 650.0, 60),)
)


@pytest.fixture
def store(tmp_path):
    return SqliteProgressStore(tmp_path / "progress.db")


@pytest.fixture
def attempt_id(store):
    started = NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, RAN_AT)
    return store.add_attempt(started).id


def record(attempt_id: int | None, **overrides: object) -> BenchRunRecord:
    fields: dict[str, object] = {
        "attempt_id": attempt_id,
        "slug": "two-sum",
        "language": Language.PYTHON,
        "ran_at": RAN_AT,
        "code_hash": "abc",
        "sizes": (100, 1000),
        "series": (USER, REFERENCE),
        "verdict": Verdict.SUBOPTIMAL,
        "confidence": Confidence.MEDIUM,
        "user_time_band": "E",
        "user_memory_band": "constant",
        "slope": 1.98,
        "r2": 0.999,
        "reference_id": "hash-map",
        "ratio": 1.3,
        "environment": {"cpu": "Apple M3 Pro", "power": "AC"},
    }
    return BenchRunRecord(**(fields | overrides))  # type: ignore[arg-type]


def stored_row(tmp_path) -> sqlite3.Row:
    connection = sqlite3.connect(tmp_path / "progress.db")
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute("SELECT * FROM bench_runs").fetchone()
    finally:
        connection.close()


def test_a_bench_run_stores_its_verdict_and_confidence(store, attempt_id, tmp_path):
    store.add_bench_run(record(attempt_id))
    row = stored_row(tmp_path)
    assert (row["attempt_id"], row["verdict"], row["confidence"]) == (
        attempt_id,
        "suboptimal",
        "medium",
    )


def test_a_bench_run_stores_its_sizes_as_json(store, attempt_id, tmp_path):
    store.add_bench_run(record(attempt_id))
    assert json.loads(stored_row(tmp_path)["sizes"]) == [100, 1000]


def test_results_hold_every_target_by_size(store, attempt_id, tmp_path):
    store.add_bench_run(record(attempt_id))
    results = json.loads(stored_row(tmp_path)["results"])
    assert results["user"]["100"] == {
        "median_ns": 900.0,
        "spread": 0.02,
        "cpu_ns": 800.0,
        "calls": 50,
        "mem_bytes": 7064,
        "mem_metric": "tracemalloc_peak",
        "status": "ok",
    }


def test_results_keep_the_call_over_the_budget(store, attempt_id, tmp_path):
    store.add_bench_run(record(attempt_id))
    results = json.loads(stored_row(tmp_path)["results"])
    assert results["user"]["1000"] == {"status": "budget_exceeded", "exceeded_ns": 5_000_000_000}


def test_the_environment_is_stored_as_json(store, attempt_id, tmp_path):
    store.add_bench_run(record(attempt_id))
    assert json.loads(stored_row(tmp_path)["env"]) == {"cpu": "Apple M3 Pro", "power": "AC"}


def test_a_references_only_run_has_no_attempt(store, tmp_path):
    store.add_bench_run(record(None, verdict=Verdict.UNKNOWN))
    assert stored_row(tmp_path)["attempt_id"] is None


def test_history_lists_the_users_medians_by_size(store, attempt_id):
    store.add_bench_run(record(attempt_id))
    assert store.bench_history("two-sum", Language.PYTHON) == (PastRun(RAN_AT, {100: 900.0}),)


def test_history_skips_references_only_runs(store):
    store.add_bench_run(record(None))
    assert store.bench_history("two-sum", Language.PYTHON) == ()


def test_history_is_per_language(store, attempt_id):
    store.add_bench_run(record(attempt_id))
    assert store.bench_history("two-sum", Language.JAVA) == ()


def test_history_runs_oldest_first(store, attempt_id):
    later = RAN_AT + timedelta(hours=1)
    store.add_bench_run(record(attempt_id, ran_at=later))
    store.add_bench_run(record(attempt_id))
    assert [run.ran_at for run in store.bench_history("two-sum", Language.PYTHON)] == [
        RAN_AT,
        later,
    ]


def test_the_latest_outcome_is_the_attempts_most_recent_run(store, attempt_id):
    later = RAN_AT + timedelta(hours=1)
    store.add_bench_run(record(attempt_id, ran_at=later, verdict=Verdict.OPTIMAL))
    store.add_bench_run(record(attempt_id))
    assert store.latest_bench_outcome(attempt_id) == BenchOutcome(
        Verdict.OPTIMAL, Confidence.MEDIUM
    )


def test_an_attempt_without_bench_runs_has_no_outcome(store, attempt_id):
    store.add_bench_run(record(None))
    assert store.latest_bench_outcome(attempt_id) is None


def test_the_bench_runs_migration_can_run_twice(tmp_path):
    script = (
        resources.files("coding_study.adapters.sqlite") / "migrations" / "0003_bench_runs.sql"
    ).read_text(encoding="utf-8")
    connection = sqlite3.connect(tmp_path / "twice.db")
    try:
        connection.executescript(script)
        connection.executescript(script)
    finally:
        connection.close()


def test_a_record_with_an_unknown_target_series_still_stores(store, attempt_id, tmp_path):
    store.add_bench_run(replace(record(attempt_id), series=()))
    assert json.loads(stored_row(tmp_path)["results"]) == {}
