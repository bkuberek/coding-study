"""`cstudy status`: where a project attempt stands, without running anything
(docs/specs/cli.md#cstudy-status)."""

from dataclasses import replace
from datetime import timedelta

import pytest

from coding_study.application.environment import Environment
from coding_study.application.project_status import OpenLevel, project_status
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import RunRecord
from coding_study.domain.errors import UsageError
from coding_study.domain.file_states import FileState, StarterChanges
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.submissions import LevelTally, LevelUnlock, SubmissionRecord
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS
from tests.project_fakes import (
    PROJECT_FOLDER,
    PROJECT_SLUG,
    ScriptedProjectProcess,
    project_environment,
)

LATER = NOW + timedelta(minutes=30)


@pytest.fixture
def environment(tmp_path) -> Environment:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment


def attempt_id(environment: Environment) -> int:
    found = environment.progress.active_attempt()
    assert found is not None
    return found.id


def submission(environment: Environment, *levels: LevelTally, minutes: int = 5):
    record = SubmissionRecord(
        attempt_id=attempt_id(environment),
        submitted_at=NOW + timedelta(minutes=minutes),
        code_hash="abc",
        graded_up_to=len(levels),
        every_level=True,
        levels=levels,
        tally=Tally(total=sum(level.total for level in levels)),
        duration_ms=300,
    )
    environment.progress.add_submission(record)
    return record


def open_level_2(environment: Environment) -> None:
    found = environment.progress.active_attempt()
    assert found is not None
    environment.progress.update_attempt(replace(found, level_unlocked=2))
    environment.progress.add_level_unlock(LevelUnlock(found.id, 2, LATER))


def test_another_kind_of_problem_is_a_usage_error(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS), toolchains=toolchains
    )
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    with pytest.raises(UsageError, match="cstudy status is for project problems"):
        project_status(environment, None, None)


def test_status_needs_an_attempt_in_progress(tmp_path):
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    with pytest.raises(UsageError, match="no attempt in progress"):
        project_status(environment, None, None)


def test_status_shows_each_open_level_and_when_it_opened(environment):
    open_level_2(environment)
    assert project_status(environment, None, None).opened == (
        OpenLevel(1, "Accounts and deposits", NOW),
        OpenLevel(2, "Transfers", LATER),
    )


def test_status_points_at_the_statement(environment):
    assert project_status(environment, None, None).statement == f".statements/{PROJECT_SLUG}.md"


def test_before_any_submission_the_next_step_is_testing(environment):
    assert project_status(environment, None, None).next_step == "cstudy test --watch"


def test_after_a_submission_the_next_step_is_passing_the_unlocked_level(environment):
    submission(environment, LevelTally(1, 1, 1, 2, 1))
    assert project_status(environment, None, None).next_step == (
        "cstudy submit once level 1 passes"
    )


def test_after_the_full_pass_the_next_step_is_done(environment):
    found = environment.progress.active_attempt()
    environment.progress.update_attempt(replace(found, first_pass_at=LATER))
    submission(environment, LevelTally(1, 1, 1, 2, 2), LevelTally(2, 1, 1, 2, 2))
    assert project_status(environment, None, None).next_step == (
        "cstudy done --rating easy|ok|hard"
    )


def test_status_shows_the_latest_test_run(environment):
    run = RunRecord(attempt_id(environment), LATER, "abc", Tally(total=4, passed=3), 700)
    environment.progress.add_test_run(run)
    assert project_status(environment, None, None).last_test_run == run


def test_status_shows_the_latest_submission(environment):
    submission(environment, LevelTally(1, 1, 1, 2, 2), minutes=1)
    latest = submission(environment, LevelTally(1, 1, 1, 2, 1), minutes=2)
    assert project_status(environment, None, None).latest_submission == latest


def test_status_keeps_the_best_count_of_each_level(environment):
    submission(environment, LevelTally(1, 1, 1, 2, 2), minutes=1)
    submission(environment, LevelTally(1, 1, 1, 2, 1), minutes=2)
    assert project_status(environment, None, None).best_per_level == (LevelTally(1, 1, 1, 2, 2),)


def test_status_reads_the_clock(environment):
    assert project_status(environment, None, None).now == NOW


# files (docs/specs/cli.md#cstudy-status)


def edit_the_folder(environment: Environment) -> None:
    """Changes the README, adds a module and deletes pyproject.toml."""
    workspace = environment.workspace
    workspace.write_text(f"{PROJECT_FOLDER}/README.md", "# mine\n")
    workspace.write_text(f"{PROJECT_FOLDER}/bank/ledger.py", "LEDGER = []\n")
    workspace.absolute(f"{PROJECT_FOLDER}/pyproject.toml").unlink()


def states(environment: Environment) -> dict[str, FileState]:
    return {file.path: file.state for file in project_status(environment, None, None).files}


def test_a_new_folder_holds_every_file_as_provided(environment):
    assert states(environment) == {
        "README.md": FileState.UNCHANGED,
        "bank/bank.py": FileState.UNCHANGED,
        "pyproject.toml": FileState.UNCHANGED,
        "tests/test_level_1.py": FileState.UNCHANGED,
    }


def test_status_tells_each_file_changed_added_or_deleted(environment):
    edit_the_folder(environment)
    assert states(environment) == {
        "README.md": FileState.MODIFIED,
        "bank/bank.py": FileState.UNCHANGED,
        "bank/ledger.py": FileState.ADDED,
        "pyproject.toml": FileState.DELETED,
        "tests/test_level_1.py": FileState.UNCHANGED,
    }


def test_status_counts_the_changes_against_the_starter(environment):
    edit_the_folder(environment)
    assert project_status(environment, None, None).starter_changes == StarterChanges(
        changed=("README.md",), added=("bank/ledger.py",), removed=("pyproject.toml",)
    )


def test_status_leaves_untracked_files_out(environment):
    environment.workspace.write_text(f"{PROJECT_FOLDER}/bank/__pycache__/bank.pyc", "")
    environment.workspace.write_text(f"{PROJECT_FOLDER}/uv.lock", "version = 1\n")
    assert "uv.lock" not in states(environment)


def test_without_a_manifest_status_compares_with_what_cstudy_provides_now(environment):
    environment.workspace.absolute(f".cs/projects/{PROJECT_SLUG}.json").unlink()
    environment.workspace.write_text(f"{PROJECT_FOLDER}/README.md", "# mine\n")
    assert states(environment)["README.md"] is FileState.MODIFIED


def test_without_a_manifest_status_writes_none(environment):
    environment.workspace.absolute(f".cs/projects/{PROJECT_SLUG}.json").unlink()
    project_status(environment, None, None)
    assert not environment.workspace.exists(f".cs/projects/{PROJECT_SLUG}.json")
