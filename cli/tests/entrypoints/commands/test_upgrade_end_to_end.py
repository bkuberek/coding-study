"""A workspace created by v0.7.0, upgraded with `cstudy doctor --fix`
(docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace).

The workspace is v0.7.0's: its `python/` project as that release shipped it (no pytest in
`pyproject.toml` or `uv.lock`; `tests/fixtures/workspace_v0_7_0/`) with a venv synced from it, and a
progress.db at schema 4 holding an attempt. The real commands then run against it, offline from
uv's cache. Only the Python project exists, so `doctor` rows about the other toolchains say so.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.workspace_setup import FsWorkspaceSetup
from coding_study.application.doctor import PYTHON_FIX
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT, progress_database_at

pytestmark = pytest.mark.slow

V0_7_0_PYTHON = Path(__file__).resolve().parents[2] / "fixtures" / "workspace_v0_7_0" / "python"
OLD_VERSION = "0.7.0"
OLD_SCHEMA = 4
OLD_ATTEMPT = 7
SLUG = "bank-project-python"
OTHER_TOOLCHAINS = ("jvm", "typescript")
runner = CliRunner()


def cs(workspace: Path, *arguments: str) -> Result:
    return runner.invoke(
        cli.app,
        [
            "--no-color",
            "--workspace",
            str(workspace),
            "--content",
            str(REPOSITORY_ROOT),
            *arguments,
        ],
    )


@dataclass(frozen=True)
class Upgrade:
    workspace: Path
    before: Result
    fix: Result
    after: Result
    started: Result
    tested: Result


@pytest.fixture(scope="module")
def upgrade(tmp_path_factory: pytest.TempPathFactory) -> Upgrade:
    workspace = tmp_path_factory.mktemp("v0-7-0-workspace")
    setup = FsWorkspaceSetup(REPOSITORY_ROOT / "runners", OLD_VERSION)
    setup.write_missing(workspace)
    for toolchain in OTHER_TOOLCHAINS:
        shutil.rmtree(workspace / toolchain)
    shutil.rmtree(workspace / "projects")
    shutil.copyfile(V0_7_0_PYTHON / "pyproject.toml", workspace / "python" / "pyproject.toml")
    shutil.copyfile(V0_7_0_PYTHON / "uv.lock", workspace / "python" / "uv.lock")
    setup.refresh_runtime(workspace)
    subprocess.run(
        PYTHON_FIX.command, cwd=workspace / PYTHON_FIX.project, check=True, capture_output=True
    )
    progress_database_at(workspace / "progress.db", OLD_SCHEMA)
    return Upgrade(
        workspace,
        before=cs(workspace, "doctor"),
        fix=cs(workspace, "doctor", "--fix"),
        after=cs(workspace, "doctor"),
        started=cs(workspace, "start", SLUG, "--no-open"),
        tested=cs(workspace, "test"),
    )


def test_before_the_fix_pytest_is_missing(upgrade: Upgrade):
    assert "WARN  python pytest not installed" in upgrade.before.output


def test_before_the_fix_the_progress_database_is_older(upgrade: Upgrade):
    assert "WARN  progress database schema 4, this cstudy uses 5" in upgrade.before.output


def test_the_fix_adds_pytest_without_the_network(upgrade: Upgrade):
    assert "ok    uv add --dev --offline pytest>=9.1 (in python)" in upgrade.fix.output


def test_the_fix_migrates_the_progress_database(upgrade: Upgrade):
    assert "migrated progress.db from schema 4 to 5" in upgrade.fix.output


def test_after_the_fix_pytest_is_installed(upgrade: Upgrade):
    assert "ok    python pytest installed" in upgrade.after.output


def test_after_the_fix_the_progress_database_is_current(upgrade: Upgrade):
    assert "ok    progress database schema 5" in upgrade.after.output


def test_after_the_fix_the_projects_folder_is_back(upgrade: Upgrade):
    assert "ok    projects" in upgrade.after.output


def test_after_the_fix_nothing_that_is_set_up_warns_or_fails(upgrade: Upgrade):
    unset = tuple(f"not set up yet (no {toolchain})" for toolchain in OTHER_TOOLCHAINS)
    flagged = [
        line
        for line in upgrade.after.output.splitlines()
        if line.startswith(("WARN", "FAIL")) and not line.endswith(unset)
    ]
    about_the_workspace = [
        line
        for line in flagged
        if "runner" not in line
        and "libraries" not in line
        and not line.startswith("WARN  installs")
    ]
    assert about_the_workspace == []


def test_the_project_starts_after_the_upgrade(upgrade: Upgrade):
    assert upgrade.started.exit_code == ExitCode.SUCCESS


def test_the_project_tests_run_in_the_upgraded_venv(upgrade: Upgrade):
    assert "pytest is missing" not in upgrade.tested.output
    assert "suite  pytest" in upgrade.tested.output


def test_the_tests_fail_only_because_the_starter_is_unfinished(upgrade: Upgrade):
    assert upgrade.tested.exit_code == ExitCode.FAILURES


def test_the_attempt_from_before_the_upgrade_survives(upgrade: Upgrade):
    store = SqliteProgressStore(upgrade.workspace / "progress.db")
    attempt = store.latest_attempt("two-sum", Language.PYTHON)
    assert (attempt.id if attempt else None) == OLD_ATTEMPT
