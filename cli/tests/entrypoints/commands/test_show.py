from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import show
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import declare_jdk, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

runner = CliRunner()
PHASE4 = Path(__file__).resolve().parents[2] / "fixtures" / "phase4" / "problems"
JVM_PROJECTS = Path(__file__).resolve().parents[2] / "fixtures" / "jvm-projects" / "problems"


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


def test_a_declared_jdk_range_is_named_in_the_metadata_line(environment):
    declare_jdk(environment.root, "0001-level-store", "{min: 24}")
    assert invoke("level-store").output.splitlines()[2] == (
        "medium · practical · Java and Kotlin: JDK 24 or newer · level 1 of 3"
    )


def test_the_default_range_is_not_named(environment):
    assert "JDK" not in invoke("level-store").output.splitlines()[2]


def test_a_java_project_names_its_one_language(tmp_path, monkeypatch):
    root = repository_root(tmp_path, JVM_PROJECTS)
    declare_jdk(root, "0001-bank-project-java", "{max: 25}")
    environment = make_environment(root)
    monkeypatch.setattr(show, "load_catalog_environment", lambda *_: environment)
    assert (
        invoke("bank-project-java")
        .output.splitlines()[2]
        .endswith(" · Java: JDK 25 or older · level 1 of 2")
    )
