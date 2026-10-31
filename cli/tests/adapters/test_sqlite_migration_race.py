"""Several processes open one brand-new progress.db at the same moment
(docs/specs/progress-and-scheduling.md#migrations)."""

import multiprocessing

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from tests.progress_race import open_at_once

WORKERS = 8
JOIN_SECONDS = 60.0
ROUNDS = 5


def race_on_new_database(path) -> list[str]:
    """Runs WORKERS processes that open a store on `path` together; returns their errors."""
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(WORKERS)
    errors = context.Queue()
    processes = [
        context.Process(target=open_at_once, args=(path, barrier, errors)) for _ in range(WORKERS)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(JOIN_SECONDS)
    assert [process.exitcode for process in processes] == [0] * WORKERS
    outcomes = [errors.get(timeout=JOIN_SECONDS) for _ in processes]
    return [outcome for outcome in outcomes if outcome]


@pytest.mark.slow
@pytest.mark.parametrize("round_number", range(ROUNDS))
def test_processes_opening_a_new_database_together_all_succeed(tmp_path, round_number):
    assert race_on_new_database(tmp_path / f"round-{round_number}" / "progress.db") == []


@pytest.mark.slow
def test_the_raced_database_is_at_the_latest_schema(tmp_path):
    path = tmp_path / "progress.db"
    race_on_new_database(path)
    assert SqliteProgressStore(path).snapshot().schema_version == 5
