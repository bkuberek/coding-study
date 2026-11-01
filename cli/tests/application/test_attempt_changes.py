"""What changed in the workspace for the web UI's notifications
(docs/specs/web-ui.md#notifications): the files of each attempt in progress, its manifest and
statement, and progress.db, compared by content between two snapshots."""

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.application.attempt_changes import (
    AttemptChanged,
    FileChanged,
    ProgressChanged,
    WatchedFolder,
    workspace_changes,
    workspace_snapshot,
)
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import Attempt
from coding_study.domain.problem import Language
from coding_study.domain.project_manifest import manifest_path
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
PROJECT = f"projects/{PROJECT_SLUG}"
STATEMENT = f".statements/{PROJECT_SLUG}.md"
PROGRESS_FILES = WatchedFolder(".", False, frozenset({"progress.db", "progress.db-wal"}))


@dataclass(frozen=True)
class Started:
    environment: Environment
    attempt: Attempt

    def write(self, path: str, content: str) -> None:
        target = self.environment.workspace.absolute(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def remove(self, path: str) -> None:
        self.environment.workspace.absolute(path).unlink()


@pytest.fixture
def project(tmp_path) -> Started:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    return Started(environment, start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt)


@pytest.fixture
def python(tmp_path) -> Started:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    environment = make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))
    request = StartRequest("two-sum", Language.PYTHON)
    return Started(environment, start_attempt(environment, request).attempt)


def changes_after(started: Started, change) -> tuple[object, ...]:
    """The changes from a snapshot before `change(started)` to one after it."""
    before = workspace_snapshot(started.environment)
    change(started)
    return workspace_changes(before, workspace_snapshot(started.environment, before))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# what a watch covers


def test_a_projects_folder_is_watched_with_its_subfolders(project):
    folders = workspace_snapshot(project.environment).folders
    assert WatchedFolder(PROJECT, True) in folders


def test_a_python_attempts_directory_is_watched_without_its_subfolders(python):
    folders = workspace_snapshot(python.environment).folders
    assert WatchedFolder("python/practice", False) in folders


def test_the_manifests_and_the_statements_are_watched(project):
    folders = workspace_snapshot(project.environment).folders
    assert {WatchedFolder(".cs/projects", False), WatchedFolder(".statements", False)} <= {*folders}


def test_progress_db_and_its_write_ahead_log_are_watched_by_name(project):
    assert PROGRESS_FILES in workspace_snapshot(project.environment).folders


def test_a_folder_that_does_not_exist_is_not_watched(tmp_path):
    environment = make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))
    environment.progress.attempts_in_progress()
    assert workspace_snapshot(environment).folders == (PROGRESS_FILES,)


# what changed


def test_nothing_changed_is_no_change(project):
    assert changes_after(project, lambda _started: None) == ()


def test_a_saved_file_is_a_file_change_with_its_sha256(project):
    changes = changes_after(project, lambda started: started.write(f"{PROJECT}/bank/bank.py", "x"))
    assert changes == (FileChanged(project.attempt.id, "bank/bank.py", sha("x")),)


def test_a_deleted_file_is_a_file_change_without_a_sha256(project):
    changes = changes_after(project, lambda started: started.remove(f"{PROJECT}/README.md"))
    assert changes == (FileChanged(project.attempt.id, "README.md", None),)


def test_a_new_file_of_a_project_is_a_file_change(project):
    changes = changes_after(project, lambda started: started.write(f"{PROJECT}/bank/ledger.py", ""))
    assert changes == (FileChanged(project.attempt.id, "bank/ledger.py", sha("")),)


@pytest.mark.parametrize("path", ["bank/__pycache__/bank.cpython-313.pyc", ".pytest_cache/x"])
def test_a_file_a_tool_wrote_is_no_change(project, path):
    assert changes_after(project, lambda started: started.write(f"{PROJECT}/{path}", "x")) == ()


def test_a_file_beside_a_single_file_attempts_file_is_no_change(python):
    changes = changes_after(python, lambda started: started.write("python/practice/other.py", "x"))
    assert changes == ()


def test_a_single_file_attempts_saved_file_is_a_file_change(python):
    changes = changes_after(python, lambda started: started.write(python.attempt.stub_path, "x\n"))
    assert changes == (FileChanged(python.attempt.id, "two_sum.py", sha("x\n")),)


def test_a_changed_statement_is_an_attempt_change(project):
    changes = changes_after(project, lambda started: started.write(STATEMENT, "# Level 2\n"))
    assert changes == (AttemptChanged(project.attempt.id, PROJECT_SLUG),)


def test_a_changed_manifest_is_an_attempt_change(project):
    def rewrite_manifest(started: Started) -> None:
        path = manifest_path(PROJECT_SLUG)
        started.write(path, started.environment.workspace.read_text(path) + "\n")

    assert changes_after(project, rewrite_manifest) == (
        AttemptChanged(project.attempt.id, PROJECT_SLUG),
    )


def test_a_write_to_progress_db_is_a_progress_change(project):
    def take_a_hint(started: Started) -> None:
        started.environment.progress.update_attempt(replace(started.attempt, hints_used=1))

    assert changes_after(project, take_a_hint) == (ProgressChanged(),)


def test_a_started_attempt_is_an_attempt_change(project):
    before = workspace_snapshot(project.environment)
    started = start_attempt(project.environment, StartRequest(PROJECT_SLUG, fresh=True)).attempt
    changes = workspace_changes(before, workspace_snapshot(project.environment, before))
    assert AttemptChanged(started.id, PROJECT_SLUG) in changes


# reading progress.db


class CountingProgress(SqliteProgressStore):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.reads = 0

    def attempts_in_progress(self) -> tuple[Attempt, ...]:
        self.reads += 1
        return super().attempts_in_progress()


def test_a_snapshot_reads_the_attempts_only_once_progress_db_changed(project):
    counting = CountingProgress(project.environment.root / "progress.db")
    environment = replace(project.environment, progress=counting)
    first = workspace_snapshot(environment)
    project.write(f"{PROJECT}/bank/bank.py", "x\n")
    workspace_snapshot(environment, first)
    assert counting.reads == 1
