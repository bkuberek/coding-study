"""The `--json` documents against their schemas in `schemas/cli/`
(docs/specs/compatibility.md#json-documents).

Each document is the real output of its command over a test workspace, validated against
`schemas/cli/<name>.schema.json`. A schema that names no field the command emits, or a command
that emits a field the schema does not name, fails here.

To cover another document:

- add its command's output to a `*_documents` fixture or a test of its own, and pass it to
  `assert_valid("<name>", document)`;
- add one `test_<name>_rejects_an_undocumented_field` over `assert_rejects_extra_field`, naming
  the path to an object of the document;
- `test_every_schema_*` already holds the new file to draft 2020-12 and to closed objects.
"""

import json
from collections.abc import Iterator
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.sqlite.schema import latest_schema_version
from coding_study.application.doctor import CheckResult, CheckStatus, DoctorReport
from coding_study.domain.progress_export import ProgressSnapshot, export_text
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import doctor, export, stats
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import (
    FIRST_CATALOG,
    FIXTURE_RUBRIC_PROBLEMS,
    REPOSITORY_ROOT,
    copy_catalog_problems,
    mark_workspace,
)
from tests.progress_fixtures import database_at_schema, read_rows
from tests.stats_fixture import fill_progress

SCHEMA_DIRECTORY = REPOSITORY_ROOT / "schemas" / "cli"
SCHEMA_FILES = sorted(SCHEMA_DIRECTORY.glob("*.schema.json"))
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
LATEST = latest_schema_version()
SCHEMAS = range(1, LATEST + 1)
EXPORT_TABLES = (
    "attempts",
    "test_runs",
    "schedule",
    "bench_runs",
    "submissions",
    "level_unlocks",
    "guide_reads",
)
UNDOCUMENTED = "undocumented_field"

runner = CliRunner()


# The harness


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIRECTORY / f"{name}.schema.json").read_text(encoding="utf-8"))


def schema_errors(name: str, document: Any) -> list[str]:
    """What is wrong with `document` as `schemas/cli/<name>.schema.json`, one line each."""
    validator = Draft202012Validator(load_schema(name))
    return [
        f"{'/'.join(str(step) for step in error.absolute_path) or '<document>'}: {error.message}"
        for error in validator.iter_errors(document)
    ]


def assert_valid(name: str, document: Any) -> None:
    assert schema_errors(name, document) == []


def with_extra_field(document: Any, path: tuple[str | int, ...]) -> Any:
    """A copy of `document` whose object at `path` has a field no schema names."""
    changed = deepcopy(document)
    target = changed
    for step in path:
        target = target[step]
    assert isinstance(target, dict)
    target[UNDOCUMENTED] = True
    return changed


def assert_rejects_extra_field(name: str, document: Any, path: tuple[str | int, ...]) -> None:
    """Fails unless the schema accepts `document` and refuses it once the object at `path` has a
    field it does not name."""
    assert_valid(name, document)
    errors = schema_errors(name, with_extra_field(document, path))
    assert len(errors) == 1
    assert UNDOCUMENTED in errors[0]


def schema_objects(schema: Any, where: str = "#") -> Iterator[tuple[str, dict[str, Any]]]:
    """Every subschema that describes an object, with its location."""
    if isinstance(schema, dict):
        if schema.get("type") == "object" or "properties" in schema:
            yield where, schema
        for key, value in schema.items():
            if key != "properties":
                yield from schema_objects(value, f"{where}/{key}")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for name, value in properties.items():
                yield from schema_objects(value, f"{where}/properties/{name}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            yield from schema_objects(value, f"{where}/{index}")


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda path: path.name)
def test_every_schema_is_draft_2020_12(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$schema"] == SCHEMA_DIALECT
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda path: path.name)
def test_every_schema_object_is_closed(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    open_objects = [
        where
        for where, subschema in schema_objects(schema)
        if subschema.get("additionalProperties") is not False
    ]
    assert open_objects == []


def test_the_schema_directory_is_not_empty():
    assert SCHEMA_FILES


# cstudy stats --json


@pytest.fixture
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


@pytest.fixture
def empty_environment(tmp_path, problems, monkeypatch):
    environment = make_environment(repository_root(tmp_path, problems, FIXTURE_RUBRIC_PROBLEMS))
    monkeypatch.setattr(stats, "load_environment", lambda *_: environment)
    return environment


@pytest.fixture
def filled_environment(empty_environment):
    fill_progress(empty_environment)
    return empty_environment


def stats_document(*arguments: str) -> Any:
    result = runner.invoke(cli.app, ["stats", "--json", *arguments])
    assert result.exit_code == ExitCode.SUCCESS
    return json.loads(result.stdout)


def test_stats_over_an_empty_database(empty_environment):
    document = stats_document()
    assert_valid("stats", document)
    assert document["attempts"] == {"finished": 0, "last_7_days": 0, "streak_days": 0}


def test_stats_over_an_empty_database_has_no_pass_rate_or_solve_time(empty_environment):
    groups = stats_document()["groups"]
    assert groups
    assert {(group["pass_rate"], group["median_solve_s"]) for group in groups} == {(None, None)}


def test_stats_over_a_populated_database(filled_environment):
    document = stats_document()
    assert_valid("stats", document)
    assert document["attempts"]["finished"] == 4


def test_stats_over_a_populated_database_has_a_pass_rate_and_a_solve_time(filled_environment):
    groups = stats_document()["groups"]
    assert any(
        isinstance(group["pass_rate"], float) and isinstance(group["median_solve_s"], int)
        for group in groups
    )


@pytest.mark.parametrize("grouping", ["pattern", "track", "lang", "difficulty"])
def test_stats_in_every_grouping(filled_environment, grouping):
    document = stats_document("--by", grouping)
    assert_valid("stats", document)
    assert document["by"] == grouping


def test_stats_since_a_date(filled_environment):
    document = stats_document("--since", "2026-10-01")
    assert_valid("stats", document)
    assert document["since"] == "2026-10-01"


def test_stats_rejects_an_undocumented_field(filled_environment):
    document = stats_document()
    for path in ((), ("groups", 0), ("attempts",), ("reviews",), ("bench",)):
        assert_rejects_extra_field("stats", document, path)


def test_stats_rejects_a_missing_field(filled_environment):
    document = stats_document()
    del document["groups"][0]["weakness"]
    assert schema_errors("stats", document)


# cstudy doctor --json


def doctor_result(*arguments: str):
    return runner.invoke(cli.app, [*arguments, "doctor", "--json"])


def stub_checks(monkeypatch: pytest.MonkeyPatch, *results: CheckResult) -> None:
    monkeypatch.setattr(doctor, "run_doctor", lambda _environment, _notify: DoctorReport(results))


PASSING = (
    CheckResult("python", CheckStatus.OK, "3.13.2"),
    CheckResult("projects", CheckStatus.OK),
    CheckResult("gradle", CheckStatus.WARN, "not found", "brew install gradle"),
)


def test_doctor_over_a_workspace_with_failing_rows(tmp_path):
    workspace = mark_workspace(tmp_path / "workspace")
    result = doctor_result("--workspace", str(workspace))
    document = json.loads(result.stdout)
    assert_valid("doctor", document)
    assert document["workspace"] == str(workspace)
    assert any(check["status"] == "fail" for check in document["checks"])
    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR


def test_doctor_without_a_workspace(tmp_path):
    document = json.loads(doctor_result("--workspace", str(tmp_path / "nowhere")).stdout)
    assert_valid("doctor", document)
    assert document["workspace"] is None


def test_doctor_with_passing_rows(monkeypatch, tmp_path):
    stub_checks(monkeypatch, *PASSING)
    result = doctor_result("--workspace", str(mark_workspace(tmp_path / "workspace")))
    document = json.loads(result.stdout)
    assert_valid("doctor", document)
    assert document["passed"] is True
    assert result.exit_code == ExitCode.SUCCESS


def test_doctor_with_a_failing_row_and_a_fix(monkeypatch):
    stub_checks(
        monkeypatch,
        *PASSING,
        CheckResult("python/.venv", CheckStatus.FAIL, "missing", "cstudy doctor --fix"),
    )
    document = json.loads(doctor_result().stdout)
    assert_valid("doctor", document)
    assert document["passed"] is False


def test_doctor_rejects_an_undocumented_field(monkeypatch):
    stub_checks(monkeypatch, *PASSING)
    document = json.loads(doctor_result().stdout)
    for path in ((), ("checks", 0)):
        assert_rejects_extra_field("doctor", document, path)


def test_doctor_rejects_a_status_it_does_not_name(monkeypatch):
    stub_checks(monkeypatch, *PASSING)
    document = json.loads(doctor_result().stdout)
    document["checks"][0]["status"] = "WARN"
    assert schema_errors("doctor", document)


# cstudy export (the file)


def export_document(environment, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The file `cstudy export` writes for the environment's progress.db."""
    monkeypatch.setattr(export, "load_environment", lambda *_: environment)
    path = tmp_path / "progress-export.json"
    assert runner.invoke(cli.app, ["export", "--out", str(path)]).exit_code == ExitCode.SUCCESS
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_environment(root: Path, number: int):
    """An environment whose progress.db is the fixture at schema `number`, migrated on first use."""
    database = database_at_schema(root / f"schema-{number}" / "progress.db", number)
    return make_environment(root, progress=SqliteProgressStore(database))


def test_an_export_over_an_empty_database(empty_environment, tmp_path, monkeypatch):
    document = export_document(empty_environment, tmp_path, monkeypatch)
    assert_valid("export", document)
    assert document["tables"] == {table: [] for table in EXPORT_TABLES}


def test_an_export_over_a_populated_database(filled_environment, tmp_path, monkeypatch):
    assert_valid("export", export_document(filled_environment, tmp_path, monkeypatch))


def test_an_export_with_rows_in_every_table(content_root, tmp_path, monkeypatch):
    environment = fixture_environment(content_root, LATEST)
    document = export_document(environment, tmp_path, monkeypatch)
    assert_valid("export", document)
    assert {table: bool(rows) for table, rows in document["tables"].items()} == dict.fromkeys(
        EXPORT_TABLES, True
    )


@pytest.mark.parametrize("number", SCHEMAS)
def test_an_export_of_the_fixture_at_each_schema_after_it_migrates(
    content_root, tmp_path, monkeypatch, number
):
    environment = fixture_environment(content_root, number)
    document = export_document(environment, tmp_path, monkeypatch)
    assert_valid("export", document)
    assert document["schema_version"] == LATEST


@pytest.mark.parametrize("number", SCHEMAS)
def test_an_export_built_at_each_schema(content_root, number):
    database = database_at_schema(content_root / "built" / "progress.db", number)
    rows = read_rows(database)
    text = export_text(
        ProgressSnapshot(number, {table: tuple(held) for table, held in rows.items()}),
        NOW + timedelta(hours=1),
    )
    document = json.loads(text)
    assert_valid("export", document)
    assert document["schema_version"] == number


def test_export_rejects_an_undocumented_field(content_root, tmp_path, monkeypatch):
    environment = fixture_environment(content_root, LATEST)
    document = export_document(environment, tmp_path, monkeypatch)
    paths: tuple[tuple[str | int, ...], ...] = ((), ("tables",))
    rows = tuple(("tables", table, 0) for table in EXPORT_TABLES)
    for path in (*paths, *rows):
        assert_rejects_extra_field("export", document, path)


def test_export_rejects_a_table_it_does_not_name(content_root, tmp_path, monkeypatch):
    environment = fixture_environment(content_root, LATEST)
    document = export_document(environment, tmp_path, monkeypatch)
    document["tables"]["undocumented_table"] = []
    assert schema_errors("export", document)


def test_export_rejects_another_version(content_root, tmp_path, monkeypatch):
    environment = fixture_environment(content_root, LATEST)
    document = export_document(environment, tmp_path, monkeypatch)
    document["version"] = 2
    assert schema_errors("export", document)
