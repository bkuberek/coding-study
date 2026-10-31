"""A TypeScript project folder graded, suite-run and type-checked through the real runner and the
workspace's `tsc` (docs/specs/runners.md#project-jobs, docs/specs/cli.md#project-problems).

The fixture problem's entry `src/bank.ts` imports sibling files, so module resolution inside a
self-contained ESM folder, outside the workspace's `typescript/` project, is part of every run. The
level test files stand in for the generated ones, in the shape problem-format.md gives them.
"""

import shutil
from pathlib import Path

import pytest

from coding_study.adapters.languages.typescript.runner import PnpmTypeChecker, TypeScriptRunner
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.application.ports import BuildFailed
from coding_study.application.project_runs import (
    GradingRun,
    SuiteRun,
    run_grading,
    run_suite,
    typecheck_project,
)
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.judging import Judgement
from coding_study.domain.levels import cases_up_to
from coding_study.domain.problem import Language, Problem
from coding_study.domain.suite_runs import Passed, SuiteReport
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import (
    REPOSITORY_ROOT,
    TYPESCRIPT_BANK_PROJECT,
    TYPESCRIPT_PROJECT_PROBLEMS,
)

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

SLUG = "bank-project-typescript"
FIXTURE = TYPESCRIPT_PROJECT_PROBLEMS / TYPESCRIPT_BANK_PROJECT
LAST_LEVEL = 2
CASES_THROUGH_LAST_LEVEL = 6
STARTER_TEST = "tests/accounts.test.ts::an account with a balance is open"
LEVEL_TESTS = {
    "tests/level-1.test.ts": """\
// Level 1 examples of bank-project-typescript, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Bank } from "../src/bank.ts";

test("ex1", () => {
  const bank = new Bank();
  assert.equal(bank.createAccount(1, "ivy"), true);
  assert.equal(bank.createAccount(2, "ivy"), false);
  assert.equal(bank.deposit(3, "ivy", 800), 800);
  assert.equal(bank.deposit(4, "max", 50), -1);
});
""",
    "tests/level-2.test.ts": """\
// Level 2 examples of bank-project-typescript, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Bank } from "../src/bank.ts";

test("ex2", () => {
  const bank = new Bank();
  assert.equal(bank.createAccount(1, "ivy"), true);
  assert.equal(bank.createAccount(2, "leo"), true);
  assert.equal(bank.deposit(3, "ivy", 500), 500);
  assert.equal(bank.transfer(4, "ivy", "leo", 200), 300);
  assert.equal(bank.transfer(5, "ivy", "leo", 400), -1);
});
""",
}
PARAMETER_PROPERTY = """\
export class Bank {
  constructor(private readonly name: string = "bank") {}

  createAccount(timestamp: number, accountId: string): boolean {
    return this.name !== accountId;
  }

  deposit(timestamp: number, accountId: string, amount: number): number {
    return amount;
  }
}
"""
TYPE_ERROR = """\
export class Bank {
  createAccount(timestamp: number, accountId: string): boolean {
    return accountId.length;
  }

  deposit(timestamp: number, accountId: string, amount: number): number {
    return amount;
  }
}
"""


def new_workspace(directory: Path) -> Path:
    return repository_root(directory, TYPESCRIPT_PROJECT_PROBLEMS)


def environment_on(workspace: Path) -> Environment:
    runner = TypeScriptRunner(workspace, REPOSITORY_ROOT / "runners", PnpmTypeChecker())
    return make_environment(
        workspace,
        toolchains=FakeToolchains(runners={Language.TYPESCRIPT: runner}),
        runner_process=SubprocessRunner(workspace / ".cs" / "runs"),
    )


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return new_workspace(tmp_path_factory.mktemp("workspace"))


@pytest.fixture(scope="module")
def environment(workspace: Path) -> Environment:
    return environment_on(workspace)


@pytest.fixture(scope="module")
def problem(environment: Environment) -> Problem:
    return environment.problems.load(SLUG)


def project_folder(workspace: Path, name: str, *overlays: str) -> Path:
    """`projects/<name>/`: the starter, each overlay of `solutions/` on it, and the level tests."""
    folder = workspace / "projects" / name
    shutil.copytree(FIXTURE / "starter", folder)
    for overlay in overlays:
        shutil.copytree(FIXTURE / "solutions" / overlay, folder, dirs_exist_ok=True)
    for path, text in LEVEL_TESTS.items():
        (folder / path).write_text(text, encoding="utf-8")
    return folder


def with_entry(folder: Path, text: str) -> Path:
    (folder / "src" / "bank.ts").write_text(text, encoding="utf-8")
    return folder


def grade(environment: Environment, problem: Problem, folder: Path, level: int) -> Judgement:
    run = GradingRun(problem, Language.TYPESCRIPT, folder, level)
    return run_grading(environment, run, print)


def suite(environment: Environment, problem: Problem, folder: Path, level: int) -> SuiteReport:
    run = SuiteRun(problem.meta, Language.TYPESCRIPT, folder, level)
    return run_suite(environment, run, print)


def test_the_reference_over_its_starter_passes_every_case_of_every_level(
    workspace, environment, problem
):
    folder = project_folder(workspace, "reference", "reference")
    judgement = grade(environment, problem, folder, LAST_LEVEL)
    assert (judgement.passed, judgement.case_count) == (True, CASES_THROUGH_LAST_LEVEL)


def test_the_bare_starter_loads_and_fails_the_level_1_cases_with_errors(
    workspace, environment, problem
):
    folder = project_folder(workspace, "starter")
    judgement = grade(environment, problem, folder, 1)
    level_1_cases = len(cases_up_to(problem.cases, 1))
    assert (judgement.load_error, judgement.count(CaseStatus.ERROR)) == (None, level_1_cases)


def test_grading_a_level_whose_method_is_missing_names_the_method(workspace, environment, problem):
    folder = project_folder(workspace, "starter-at-level-2")
    load_error = grade(environment, problem, folder, LAST_LEVEL).load_error
    assert load_error is not None
    assert "transfer" in load_error.message


def test_the_suite_runs_the_starters_tests_and_the_unlocked_levels_files(
    workspace, environment, problem
):
    folder = project_folder(workspace, "suite-level-1", "reference")
    report = suite(environment, problem, folder, 1)
    assert [(test.test_id, type(test.outcome)) for test in report.tests] == [
        (STARTER_TEST, Passed),
        ("tests/level-1.test.ts::ex1", Passed),
    ]


def test_the_suite_of_the_last_level_runs_every_levels_file(workspace, environment, problem):
    folder = project_folder(workspace, "suite-level-2", "reference")
    report = suite(environment, problem, folder, LAST_LEVEL)
    assert [test.test_id for test in report.tests][-1] == "tests/level-2.test.ts::ex2"


def test_a_parameter_property_does_not_load(workspace, environment, problem):
    folder = with_entry(project_folder(workspace, "parameter-property"), PARAMETER_PROPERTY)
    load_error = grade(environment, problem, folder, 1).load_error
    assert load_error is not None
    assert "parameter property" in load_error.message


@pytest.fixture(scope="module")
def checked_workspace(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    """A workspace whose `typescript/` project has the practice workspace's `node_modules`."""
    workspace = new_workspace(tmp_path_factory.mktemp("checked-workspace"))
    typescript = workspace / "typescript"
    typescript.mkdir()
    shutil.copyfile(practice_workspace / "typescript" / "package.json", typescript / "package.json")
    (typescript / "node_modules").symlink_to(practice_workspace / "typescript" / "node_modules")
    return workspace


def type_check(workspace: Path, folder: Path) -> BuildFailed | None:
    return typecheck_project(environment_on(workspace), Language.TYPESCRIPT, folder)


def test_the_reference_folder_type_checks(checked_workspace):
    folder = project_folder(checked_workspace, "reference", "reference")
    assert type_check(checked_workspace, folder) is None


def test_a_type_error_fails_the_check_with_the_file_relative_to_the_workspace(checked_workspace):
    folder = with_entry(project_folder(checked_workspace, "type-error", "reference"), TYPE_ERROR)
    failure = type_check(checked_workspace, folder)
    assert failure is not None
    assert failure.diagnostics[0].startswith("projects/type-error/src/bank.ts(3,5): error TS2322")


def test_the_check_refuses_syntax_that_node_cannot_strip(checked_workspace):
    folder = project_folder(checked_workspace, "erasable", "reference")
    failure = type_check(checked_workspace, with_entry(folder, PARAMETER_PROPERTY))
    assert failure is not None
    assert any("error TS1294" in line for line in failure.diagnostics)
