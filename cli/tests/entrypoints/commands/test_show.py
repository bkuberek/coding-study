from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import show
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

runner = CliRunner()
PHASE4 = Path(__file__).resolve().parents[2] / "fixtures" / "phase4" / "problems"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, PHASE4))
    monkeypatch.setattr(show, "load_catalog_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["show", *arguments])


def test_prints_the_rendered_statement(environment):
    assert invoke("level-store").output.startswith("# Level Store\n\nmedium · practical")


def test_exits_0(environment):
    assert invoke("level-store").exit_code == ExitCode.SUCCESS


def test_a_locked_level_exits_3(environment):
    result = invoke("level-store", "--level", "3")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: level 3 is locked; pass level 1 with cstudy test first\n",
    )


def test_an_unknown_problem_exits_3(environment):
    assert invoke("nope").exit_code == ExitCode.USAGE_ERROR


def test_prints_an_item_prompt(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, PHASE4, FIXTURE_TRACKS))
    monkeypatch.setattr(show, "load_catalog_environment", lambda *_: environment)
    assert invoke("url-shortener").output.startswith("# URL Shortener\n\nmedium · system-design")


def test_a_solution_file_path_shows_its_problem(environment):
    path = environment.root / "python/practice/level_store.py"
    assert invoke(str(path)).output == invoke("level-store").output


def test_a_path_outside_the_layout_exits_3(environment):
    path = environment.root / "notes/level-store.py"
    assert (invoke(str(path)).exit_code, invoke(str(path)).stderr) == (
        ExitCode.USAGE_ERROR,
        f"error: not a solution file in this workspace: {path}\n",
    )
