"""`cstudy solution` output for a project problem (docs/specs/cli.md#cstudy-solution)."""

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import solution
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

runner = CliRunner()


@pytest.fixture
def output(tmp_path, monkeypatch) -> list[str]:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    monkeypatch.setattr(solution, "load_environment", lambda *_: environment)
    result = runner.invoke(cli.app, ["solution", PROJECT_SLUG, "--yes"])
    return [line.strip() for line in result.output.splitlines()]


def test_the_reference_names_each_changed_file(output):
    assert "bank/bank.py (changed)" in output


def test_a_changed_file_shows_as_a_diff_against_the_starter(output):
    assert "+++ reference/bank/bank.py" in output
