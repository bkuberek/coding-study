import pytest
from typer.testing import CliRunner

from coding_study.domain.scaffold import TemplateName
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import new, verify
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment

runner = CliRunner()


@pytest.fixture
def environment(content_root, monkeypatch):
    environment = make_environment(content_root)
    monkeypatch.setattr(new, "load_environment", lambda *_: environment)
    monkeypatch.setattr(verify, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["new", *arguments])


def test_prints_the_new_directory(environment):
    assert invoke("max-gap").output.splitlines()[0] == (
        "created  problems/0003-max-gap  (array template, draft)"
    )


def test_prints_the_authoring_workflow_with_the_slug(environment):
    lines = invoke("max-gap").output.splitlines()
    assert lines[2:5] == [
        "next steps (docs/specs/authoring.md#workflow)",
        "  2. Write problem.md: statement, input, output, constraints, in original wording",
        "     cstudy verify max-gap --static",
    ]


def test_says_where_to_trim_the_languages(environment):
    assert invoke("max-gap").output.splitlines()[1] == (
        "languages  meta.yaml lists the languages to write references in; remove the ones you "
        "do not practice, and their reference files"
    )


def test_ends_with_the_ready_gate(environment):
    assert invoke("max-gap").output.splitlines()[-1] == (
        "     cstudy verify max-gap --oracle --ladder --require-ready"
    )


def test_flags_reach_the_scaffold(environment):
    invoke("same-tree", "--from-template", "tree", "--title", "Same Tree?", "--difficulty", "easy")
    meta = environment.problems.load("same-tree").meta
    assert (meta.title, meta.difficulty, meta.patterns) == ("Same Tree?", "easy", ("trees",))


def test_an_existing_slug_exits_3(environment):
    assert invoke("two-sum").exit_code == ExitCode.USAGE_ERROR


def test_an_unknown_template_exits_3(environment):
    assert invoke("x", "--from-template", "graph").exit_code == ExitCode.USAGE_ERROR


@pytest.mark.parametrize("template", list(TemplateName))
def test_cs_verify_static_passes_once_the_placeholders_are_replaced(environment, template):
    invoke("scaffolded", "--from-template", template)
    for path in (environment.root / "problems" / "0003-scaffolded").rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace("TODO", "Written"))
    result = runner.invoke(cli.app, ["verify", "scaffolded", "--static"])
    assert (result.exit_code, "warning" in result.output) == (0, False)
