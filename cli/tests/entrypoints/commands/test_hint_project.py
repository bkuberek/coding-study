"""`cstudy hint` on a project problem (docs/specs/cli.md#cstudy-hint)."""

from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import hint as hint_command
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

runner = CliRunner()
HINTS = "\n## Hints\n\n### Hint 1\n\nUse a dictionary.\n\n### Hint 2\n\nCheck both accounts.\n"


def test_the_hint_of_a_locked_level_says_when_it_opens(tmp_path, monkeypatch):
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    problem_md = tmp_path / "problems" / "0001-bank-project-python" / "problem.md"
    problem_md.write_text(problem_md.read_text(encoding="utf-8") + HINTS, encoding="utf-8")
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    monkeypatch.setattr(hint_command, "load_environment", lambda *_: environment)
    runner.invoke(cli.app, ["hint"])
    assert runner.invoke(cli.app, ["hint"]).output == "no more hints until level 2 opens\n"
