"""What a command does with a progress.db at an older schema, a newer one, or a backup that fails
(docs/specs/compatibility.md#migrations)."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from coding_study.adapters.sqlite.schema import latest_schema_version
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import mark_workspace
from tests.progress_fixtures import backups_in, database_at_schema, stored_schema

runner = CliRunner()
LATEST = latest_schema_version()
EXPORT = {"format": "coding-study-progress", "version": 1, "schema_version": 1, "tables": {}}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return mark_workspace(tmp_path / "workspace")


def cs(workspace: Path, content: Path, *arguments: str) -> Result:
    return runner.invoke(
        cli.app,
        ["--no-color", "--workspace", str(workspace), "--content", str(content), *arguments],
    )


def newer_database(workspace: Path) -> bytes:
    path = database_at_schema(workspace / "progress.db", LATEST)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (LATEST + 1,))
    return path.read_bytes()


@pytest.mark.parametrize(
    "command",
    [
        ["export"],
        ["import"],
        ["stats"],
        ["status"],
        ["history", "two-sum"],
        ["next"],
        ["list"],
        ["hint"],
        ["abort"],
        ["done", "--rating", "ok"],
        ["reset", "--yes"],
    ],
    ids=" ".join,
)
def test_a_newer_database_is_refused_by_the_command_that_opens_it(workspace, content_root, command):
    (workspace / "progress-export.json").write_text(json.dumps(EXPORT))
    before = newer_database(workspace)
    result = cs(workspace, content_root, *command)
    assert (
        result.exit_code,
        result.output.strip(),
        (workspace / "progress.db").read_bytes(),
        backups_in(workspace),
    ) == (
        ExitCode.USAGE_ERROR,
        f"error: progress.db uses schema {LATEST + 1}, newer than the {LATEST} this cstudy "
        "reads: upgrade cstudy",
        before,
        [],
    )


def test_the_first_command_backs_up_an_older_database_and_says_so_on_stderr(
    workspace, content_root
):
    database_at_schema(workspace / "progress.db", 3)
    result = cs(workspace, content_root, "export")
    (backup,) = backups_in(workspace)
    assert (result.exit_code, stored_schema(workspace / "progress.db")) == (0, LATEST)
    assert result.stderr == (
        f"progress.db: backed up to .cs/backups/{backup.name}; migrated from schema 3 to {LATEST}\n"
    )
    assert "backed up" not in result.stdout


def test_a_later_command_makes_no_second_backup(workspace, content_root):
    database_at_schema(workspace / "progress.db", 3)
    cs(workspace, content_root, "export")
    result = cs(workspace, content_root, "export")
    assert (len(backups_in(workspace)), result.stderr) == (1, "")


def test_a_backup_that_fails_stops_the_command_with_exit_4_and_changes_nothing(
    workspace, content_root
):
    path = database_at_schema(workspace / "progress.db", 3)
    (workspace / ".cs" / "backups").write_text("a file where the folder goes")
    before = path.read_bytes()
    result = cs(workspace, content_root, "export")
    assert (result.exit_code, path.read_bytes(), stored_schema(path)) == (
        ExitCode.ENVIRONMENT_ERROR,
        before,
        3,
    )
    assert result.stderr.startswith("error: cannot back up progress.db before migrating it: ")
    assert result.stderr.endswith("; nothing changed\n")
