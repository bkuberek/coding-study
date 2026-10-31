"""The pilot project's files from `cstudy start` to `cstudy start --restore`: edit, add and delete
files, read each file's state in `cstudy status --json`, then write files back
(docs/specs/cli.md#cstudy-status, cli.md#restoring-a-file).

The workspace is a temporary directory holding a copy of the pilot; the real Python test
generator writes the level tests, and nothing runs the project's code.
"""

import json
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.application.environment import Environment
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start, status
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import CATALOG_PROBLEMS

pytestmark = pytest.mark.slow

SLUG = "bank-project-python"
PILOT = CATALOG_PROBLEMS / "0249-bank-project-python"
FOLDER = Path("projects") / SLUG
ENTRY = "bank/bank.py"
MODELS = "bank/models.py"
LEDGER = "bank/ledger.py"
LEVEL_1_TESTS = "tests/test_level_1.py"
RESTORED = (ENTRY, MODELS, LEVEL_1_TESTS)
runner = CliRunner()


@pytest.fixture(scope="module")
def environment(tmp_path_factory: pytest.TempPathFactory) -> Environment:
    catalog = tmp_path_factory.mktemp("catalog")
    shutil.copytree(PILOT, catalog / PILOT.name)
    root = repository_root(tmp_path_factory.mktemp("workspace"), catalog)
    toolchains = FakeToolchains(project_test_generators={Language.PYTHON: PythonTestGenerator()})
    return make_environment(root, toolchains=toolchains)


@pytest.fixture(scope="module")
def cstudy(environment: Environment) -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        for command in (start, status):
            patch.setattr(command, "load_environment", lambda *_: environment)
        yield


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, list(arguments))


@dataclass(frozen=True)
class Played:
    steps: dict[str, Result]
    """Every command, in order."""
    generated: str
    """Level 1's tests as `cstudy start` wrote them."""


@pytest.fixture(scope="module")
def played(environment: Environment, cstudy: None) -> Played:
    folder = environment.root / FOLDER
    steps = {"start": cs("start", SLUG, "--no-open")}
    generated = (folder / LEVEL_1_TESTS).read_text(encoding="utf-8")
    (folder / ENTRY).write_text((folder / ENTRY).read_text() + "\n# mine\n")
    (folder / LEDGER).write_text("LEDGER: list[int] = []\n")
    (folder / MODELS).unlink()
    (folder / LEVEL_1_TESTS).write_text("# my own tests\n")
    steps["status"] = cs("status", "--json")
    for path in RESTORED:
        steps[f"restore {path}"] = cs("start", SLUG, "--restore", path)
    steps["status after restoring"] = cs("status", "--json")
    return Played(steps, generated)


def files(result: Result) -> dict[str, object]:
    return json.loads(result.stdout)["files"]


def states(result: Result) -> dict[str, tuple[str, str]]:
    entries = files(result)["entries"]
    assert isinstance(entries, list)
    return {entry["path"]: (entry["origin"], entry["state"]) for entry in entries}


def starter_text(path: str) -> str:
    return (PILOT / "starter" / path).read_text(encoding="utf-8")


def folder_text(environment: Environment, path: str) -> str:
    return (environment.root / FOLDER / path).read_text(encoding="utf-8")


def test_start_counts_the_starter_and_level_1s_tests(played):
    assert f"project    {FOLDER} (6 files)" in played.steps["start"].output


def test_status_tells_each_files_origin_and_state(played):
    assert states(played.steps["status"]) == {
        "README.md": ("starter", "unchanged"),
        ENTRY: ("starter", "modified"),
        LEDGER: ("yours", "added"),
        MODELS: ("starter", "deleted"),
        "pyproject.toml": ("starter", "unchanged"),
        "tests/conftest.py": ("starter", "unchanged"),
        LEVEL_1_TESTS: ("level", "modified"),
    }


def test_status_counts_the_changes_against_the_starter(played):
    found = files(played.steps["status"])
    assert (found["changed"], found["added"], found["removed"]) == ([ENTRY], [LEDGER], [MODELS])


@pytest.mark.parametrize("path", RESTORED)
def test_each_restore_exits_0(played, path):
    assert played.steps[f"restore {path}"].exit_code == ExitCode.SUCCESS


def test_restore_brings_back_a_modified_starter_file(environment, played):
    assert folder_text(environment, ENTRY) == starter_text(ENTRY)


def test_restore_brings_back_a_deleted_starter_file(environment, played):
    assert folder_text(environment, MODELS) == starter_text(MODELS)


def test_restore_brings_back_the_generated_tests(environment, played):
    assert folder_text(environment, LEVEL_1_TESTS) == played.generated


def test_after_restoring_only_your_file_differs_from_what_cstudy_provided(played):
    after = states(played.steps["status after restoring"])
    assert {path: state for path, state in after.items() if state[1] != "unchanged"} == {
        LEDGER: ("yours", "added")
    }
