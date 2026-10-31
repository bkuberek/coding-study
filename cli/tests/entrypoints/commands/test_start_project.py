"""`cstudy start` output for a project problem (docs/specs/cli.md#cstudy-start)."""

import json

import pytest
from typer.testing import CliRunner

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.adapters.languages.rust.test_generator import RustTestGenerator
from coding_study.application.ide_files import IdeRequest
from coding_study.domain.ide import Ide
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start
from coding_study.entrypoints.commands.ide import write_ide_files
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import PROJECT_PROBLEMS, RUST_PROJECT_PROBLEMS

runner = CliRunner()
SLUG = "bank-project-python"
FOLDER = f"projects/{SLUG}"
STATEMENT = f".statements/{SLUG}.md"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    toolchains = FakeToolchains(project_test_generators={Language.PYTHON: PythonTestGenerator()})
    environment = make_environment(
        repository_root(tmp_path, PROJECT_PROBLEMS), toolchains=toolchains
    )
    monkeypatch.setattr(start, "load_environment", lambda *_: environment)
    return environment


def cs_start(*arguments: str):
    return runner.invoke(cli.app, ["start", SLUG, *arguments])


def test_start_reports_the_folder_its_entry_and_its_tests(environment):
    assert cs_start("--no-open").output.splitlines() == [
        f"{SLUG} · medium · practical · python · project",
        f"project    {FOLDER} (4 files)",
        "entry      bank/bank.py: Bank",
        "tests      tests/test_level_1.py (1 test)",
        f"statement  {STATEMENT}",
        "level      1 of 2: Accounts and deposits",
        "next       cstudy test --watch, then cstudy submit",
    ]


def test_a_resumed_project_says_so(environment):
    cs_start("--no-open")
    assert "attempt    resumed" in cs_start("--no-open").output.splitlines()


def test_start_opens_the_folder_and_the_statement(environment):
    cs_start()
    assert environment.editor.opened == [
        [environment.workspace.absolute(FOLDER), environment.workspace.absolute(STATEMENT)]
    ]


def test_another_language_exits_3(environment):
    result = cs_start("--lang", "kotlin", "--no-open")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        f"error: {SLUG} is solved in python only\n",
    )


# a Rust project joins rust-analyzer's linked projects (docs/specs/cli.md#cstudy-start)

RUST_SLUG = "bank-project-rust"
VSCODE_SETTINGS = ".vscode/settings.json"


@pytest.fixture
def rust_environment(tmp_path, monkeypatch):
    toolchains = FakeToolchains(project_test_generators={Language.RUST: RustTestGenerator()})
    environment = make_environment(
        repository_root(tmp_path, RUST_PROJECT_PROBLEMS), toolchains=toolchains
    )
    monkeypatch.setattr(start, "load_environment", lambda *_: environment)
    return environment


def start_rust(*arguments: str):
    return runner.invoke(cli.app, ["start", RUST_SLUG, "--no-open", *arguments])


def linked_projects(environment) -> list[str]:
    settings = json.loads((environment.root / VSCODE_SETTINGS).read_text())
    return settings["rust-analyzer.linkedProjects"]


def test_a_rust_start_links_its_folder_in_the_vscode_settings_cstudy_wrote(rust_environment):
    write_ide_files(rust_environment.root, IdeRequest((Ide.VSCODE,)))
    start_rust()
    assert linked_projects(rust_environment) == [
        "rust/Cargo.toml",
        f"projects/{RUST_SLUG}/Cargo.toml",
    ]


def test_a_rust_start_says_it_updated_the_vscode_files(rust_environment):
    write_ide_files(rust_environment.root, IdeRequest((Ide.VSCODE,)))
    assert "ide        vscode · 1 updated" in start_rust().output.splitlines()


def test_a_rust_start_writes_no_ide_file_where_cstudy_ide_never_ran(rust_environment):
    start_rust()
    assert not (rust_environment.root / ".vscode").exists()


def test_a_resumed_rust_project_leaves_the_ide_files_alone(rust_environment):
    start_rust()
    write_ide_files(rust_environment.root, IdeRequest((Ide.VSCODE,)))
    (rust_environment.root / VSCODE_SETTINGS).write_text("{}\n")
    assert [line for line in start_rust().output.splitlines() if "vscode" in line] == []
