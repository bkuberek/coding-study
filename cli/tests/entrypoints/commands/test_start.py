from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.domain.config import Config
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import RecordingEditor, repository_root

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUB = "python/practice/two_sum.py"


@pytest.fixture
def editor() -> RecordingEditor:
    return RecordingEditor()


@pytest.fixture
def environment(tmp_path, editor, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PRACTICE), editor=editor)
    monkeypatch.setattr(start, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["start", *arguments])


def test_prints_the_problem_and_the_files(environment):
    assert invoke("two-sum").output.splitlines() == [
        "two-sum · easy · arrays-hashing · python",
        f"stub       {STUB}",
        "statement  .statements/two-sum.md",
        "next       cstudy test --watch",
    ]


def test_exits_0(environment):
    assert invoke("two-sum").exit_code == 0


def test_writes_the_stub(environment):
    invoke("two-sum")
    assert environment.workspace.read_text(STUB).startswith("def two_sum(nums, target):")


def test_opens_the_stub_and_statement_in_the_editor(environment, editor):
    invoke("two-sum")
    root = environment.root
    assert editor.opened == [[root / STUB, root / ".statements/two-sum.md"]]


def test_no_open_skips_the_editor(environment, editor):
    invoke("two-sum", "--no-open")
    assert editor.opened == []


def test_config_can_turn_the_editor_off(environment, editor, monkeypatch):
    quiet = replace(environment, config=Config(open_on_start=False))
    monkeypatch.setattr(start, "load_environment", lambda *_: quiet)
    invoke("two-sum")
    assert editor.opened == []


def test_editor_problems_are_reported(environment, monkeypatch):
    broken = replace(environment, editor=RecordingEditor("set $VISUAL or $EDITOR"))
    monkeypatch.setattr(start, "load_environment", lambda *_: broken)
    assert invoke("two-sum").output.splitlines()[-1] == "editor     set $VISUAL or $EDITOR"


def test_resuming_says_so(environment):
    invoke("two-sum")
    assert "attempt    resumed" in invoke("two-sum").output.splitlines()


def test_fresh_reports_the_archived_file(environment):
    invoke("two-sum")
    environment.workspace.write_text(STUB, "mine\n")
    lines = invoke("two-sum", "--fresh").output.splitlines()
    assert "archived   .archive/two-sum/1-python/two_sum.py" in lines


def test_timer_is_stored(environment):
    invoke("two-sum", "--timer", "25m")
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    assert attempt.time_limit_s == 1500


def test_invalid_timer_is_a_usage_error(environment):
    result = invoke("two-sum", "--timer", "soon")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        'error: invalid timer "soon": use a duration such as 25m, 1h or 1h30m\n',
    )


def test_unknown_problem_is_a_usage_error(environment):
    assert invoke("three-sum").exit_code == ExitCode.USAGE_ERROR


def test_language_not_set_up_is_an_environment_error(environment):
    result = invoke("two-sum", "--lang", "kotlin")
    assert (result.exit_code, result.stderr) == (
        ExitCode.ENVIRONMENT_ERROR,
        "error: kotlin stub generator is not set up yet\n",
    )


def test_outside_a_workspace_is_a_usage_error_pointing_at_cs_init(tmp_path, monkeypatch):
    monkeypatch.delenv("CSTUDY_WORKSPACE", raising=False)
    monkeypatch.chdir(tmp_path)
    result = invoke("two-sum")
    assert (result.exit_code, "run cstudy init" in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_a_solution_file_path_starts_its_problem_in_its_language(environment):
    result = invoke(str(environment.root / STUB), "--no-open")
    assert (result.exit_code, result.output.splitlines()[0]) == (
        0,
        "two-sum · easy · arrays-hashing · python",
    )
