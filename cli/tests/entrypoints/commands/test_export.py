import json

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import export, import_progress, stats
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment, repository_root
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, copy_catalog_problems
from tests.stats_fixture import fill_progress

runner = CliRunner()
EXPORT_FILE = "progress-export.json"
COUNTS = "attempts 6 · test_runs 4 · schedule 3 · bench_runs 3"


@pytest.fixture
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


def environment_on(tmp_path_factory, problems, name: str):
    root = repository_root(tmp_path_factory.mktemp(name), problems, FIXTURE_TRACKS)
    return make_environment(root)


@pytest.fixture
def source(tmp_path_factory, problems, monkeypatch):
    """A repository whose progress.db holds tests/stats_fixture.py."""
    environment = environment_on(tmp_path_factory, problems, "source")
    fill_progress(environment)
    monkeypatch.setattr(export, "load_environment", lambda *_: environment)
    return environment


@pytest.fixture
def target(tmp_path_factory, problems, monkeypatch):
    """Another repository with an empty progress.db."""
    environment = environment_on(tmp_path_factory, problems, "target")
    monkeypatch.setattr(import_progress, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, list(arguments))


def stats_output(environment, monkeypatch, *arguments: str) -> str:
    monkeypatch.setattr(stats, "load_environment", lambda *_: environment)
    return invoke("stats", *arguments).output


def exported(source) -> str:
    invoke("export")
    return (source.root / EXPORT_FILE).read_text()


def test_export_writes_the_file_at_the_repository_root(source):
    invoke("export")
    assert (source.root / EXPORT_FILE).is_file()


def test_export_reports_the_rows_and_the_file(source):
    assert invoke("export").output.splitlines() == [
        f"exported  {COUNTS}",
        f"file      {EXPORT_FILE}",
    ]


def test_export_names_its_format(source):
    assert json.loads(exported(source))["format"] == "coding-study-progress"


def test_export_writes_one_row_per_line(source):
    lines = exported(source).splitlines()
    assert sum(1 for line in lines if line.lstrip().startswith('{"id": ')) == 13


def test_export_to_another_file(source, tmp_path):
    path = tmp_path / "backup" / "progress.json"
    path.parent.mkdir()
    invoke("export", "--out", str(path))
    assert json.loads(path.read_text())["tables"]["schedule"][0]["slug"] == "two-sum"


def test_export_to_a_missing_directory_is_a_usage_error(source, tmp_path):
    result = invoke("export", "--out", str(tmp_path / "missing" / "progress.json"))
    assert result.exit_code == ExitCode.USAGE_ERROR


def test_an_imported_export_gives_identical_stats(source, target, monkeypatch, tmp_path):
    path = tmp_path / EXPORT_FILE
    invoke("export", "--out", str(path))
    invoke("import", str(path))
    assert stats_output(target, monkeypatch) == stats_output(source, monkeypatch)


@pytest.mark.parametrize("grouping", ["track", "lang", "difficulty"])
def test_an_imported_export_gives_identical_stats_in_every_grouping(
    source, target, monkeypatch, tmp_path, grouping
):
    path = tmp_path / EXPORT_FILE
    invoke("export", "--out", str(path))
    invoke("import", str(path))
    original = stats_output(source, monkeypatch, "--by", grouping)
    assert stats_output(target, monkeypatch, "--by", grouping) == original


def test_an_imported_export_holds_the_same_rows(source, target, tmp_path):
    path = tmp_path / EXPORT_FILE
    invoke("export", "--out", str(path))
    invoke("import", str(path))
    assert target.progress.snapshot() == source.progress.snapshot()


def test_import_reports_the_rows(source, target, tmp_path):
    path = tmp_path / EXPORT_FILE
    invoke("export", "--out", str(path))
    assert invoke("import", str(path)).output.splitlines() == [
        f"imported  {COUNTS}",
        "into      progress.db",
    ]


def test_import_reads_the_repository_root_file_by_default(source, target):
    (target.root / EXPORT_FILE).write_text(exported(source))
    assert invoke("import").exit_code == ExitCode.SUCCESS


def test_import_into_a_database_with_progress_is_a_usage_error(source, monkeypatch):
    monkeypatch.setattr(import_progress, "load_environment", lambda *_: source)
    invoke("export")
    result = invoke("import")
    assert (result.exit_code, "already holds progress" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_import_without_an_export_is_a_usage_error(target):
    result = invoke("import")
    assert (result.exit_code, "cstudy export" in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_import_of_a_file_that_is_not_json_is_a_usage_error(target, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{")
    assert invoke("import", str(path)).exit_code == ExitCode.USAGE_ERROR


def test_import_of_another_json_document_is_a_usage_error(target, tmp_path):
    path = tmp_path / "other.json"
    path.write_text("[]")
    result = invoke("import", str(path))
    assert "not a coding-study progress export" in result.stderr


def test_commands_are_registered():
    names = {command.name for command in cli.app.registered_commands}
    assert {"export", "import"} <= names
