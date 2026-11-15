"""Several processes open one progress.db at the same moment, a brand-new one or one at an older
schema (docs/specs/compatibility.md#migrations)."""

import multiprocessing

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.sqlite.schema import latest_schema_version
from tests.progress_fixtures import backups_in, database_at_schema, read_rows, stored_schema
from tests.progress_race import open_at_once

WORKERS = 8
JOIN_SECONDS = 60.0
ROUNDS = 5
OLDER_SCHEMA = 3


def race_on_database(path) -> list[str]:
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
    assert race_on_database(tmp_path / f"round-{round_number}" / "progress.db") == []


@pytest.mark.slow
def test_the_raced_database_is_at_the_latest_schema(tmp_path):
    path = tmp_path / "progress.db"
    race_on_database(path)
    assert SqliteProgressStore(path).snapshot().schema_version == latest_schema_version()


@pytest.mark.slow
@pytest.mark.parametrize("round_number", range(ROUNDS))
def test_processes_opening_an_older_database_together_make_one_backup_and_migrate_once(
    tmp_path, capfd, round_number
):
    path = database_at_schema(tmp_path / f"round-{round_number}" / "progress.db", OLDER_SCHEMA)
    before = read_rows(path)
    errors = race_on_database(path)
    (backup,) = backups_in(path.parent)
    assert (
        errors,
        stored_schema(path),
        stored_schema(backup),
        read_rows(backup),
        capfd.readouterr().err.count("progress.db: backed up to "),
    ) == ([], latest_schema_version(), OLDER_SCHEMA, before, 1)
