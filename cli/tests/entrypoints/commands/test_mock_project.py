"""`cstudy mock` with a project problem in scope (docs/specs/cli.md#cstudy-mock)."""

import pytest
from typer.testing import CliRunner

from coding_study.domain.attempts import AttemptMode
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import mock
from tests.project_fakes import (
    PROJECT_FOLDER,
    PROJECT_SLUG,
    ScriptedProjectProcess,
    project_environment,
)

runner = CliRunner()
META = "problems/0001-bank-project-python/meta.yaml"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    meta = tmp_path / META
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    meta.write_text(meta.read_text(encoding="utf-8").replace("status: draft", "status: ready"))
    monkeypatch.setattr(mock, "load_environment", lambda *_: environment)
    return environment


def run_mock():
    return runner.invoke(
        cli.app, ["mock", "--track", "practical", "--lang", "python", "--count", "1"]
    )


def test_a_project_problem_starts_as_a_mock_attempt(environment):
    run_mock()
    assert environment.progress.active_attempt(PROJECT_SLUG).mode is AttemptMode.MOCK


def test_the_mock_report_names_the_project_folder(environment):
    assert f"   project    {PROJECT_FOLDER}" in run_mock().output.splitlines()
