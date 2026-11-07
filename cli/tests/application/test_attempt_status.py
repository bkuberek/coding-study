"""`cstudy status`: where an attempt in progress stands, without running anything
(docs/specs/cli.md#cstudy-status)."""

from dataclasses import replace
from datetime import timedelta

import pytest

from coding_study.application.attempt_status import (
    HintCount,
    OpenLevel,
    ProjectStanding,
    attempt_status,
)
from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import RunRecord
from coding_study.domain.errors import UsageError
from coding_study.domain.file_states import FileState, StarterChanges
from coding_study.domain.items import EntryKind
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Track
from coding_study.domain.submissions import LevelTally, LevelUnlock, SubmissionRecord
from tests.fakes import NOW
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


def project_of(environment: Environment) -> ProjectStanding:
    found = attempt_status(environment, None, None).project
    assert found is not None
    return found


def test_status_needs_an_attempt_in_progress(tmp_path):
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    with pytest.raises(UsageError, match="no attempt in progress"):
        attempt_status(environment, None, None)


def test_status_shows_each_open_level_and_when_it_opened(environment):
    open_level_2(environment)
    assert attempt_status(environment, None, None).opened == (
        OpenLevel(1, "Accounts and deposits", NOW),
        OpenLevel(2, "Transfers", LATER),
    )


def test_status_points_at_the_statement(environment):
    assert attempt_status(environment, None, None).statement == f".statements/{PROJECT_SLUG}.md"


def test_a_project_attempt_is_of_the_project_kind(environment):
    found = attempt_status(environment, None, None)
    assert (found.kind, found.track) == (EntryKind.PROJECT, Track.PRACTICAL)


def test_a_project_attempts_file_is_its_folder(environment):
    assert attempt_status(environment, None, None).file == PROJECT_FOLDER


def test_a_project_without_hints_counts_none(environment):
    assert attempt_status(environment, None, None).hints == HintCount(0, 0, None)


HINTS = """
## Hints

### Hint 1

Keep balances in a dictionary.

### Hint 2

Check both accounts before moving money.
"""


def use_hints(environment: Environment, used: int) -> None:
    problem_md = environment.root / "problems" / "0001-bank-project-python" / "problem.md"
    problem_md.write_text(problem_md.read_text(encoding="utf-8") + HINTS, encoding="utf-8")
    found = environment.progress.active_attempt()
    assert found is not None
    environment.progress.update_attempt(replace(found, hints_used=used))


def test_hints_count_the_used_of_the_problems_hints(environment):
    use_hints(environment, 0)
    assert attempt_status(environment, None, None).hints == HintCount(0, 2, None)


def test_hints_name_the_level_the_next_hint_opens_with(environment):
    use_hints(environment, 1)
    assert attempt_status(environment, None, None).hints == HintCount(1, 2, 2)


def test_once_its_level_opens_the_next_hint_is_not_locked(environment):
    use_hints(environment, 1)
    open_level_2(environment)
    assert attempt_status(environment, None, None).hints.locked_until_level is None


def test_with_every_hint_used_none_is_locked(environment):
    use_hints(environment, 2)
    assert attempt_status(environment, None, None).hints == HintCount(2, 2, None)


def test_a_native_project_leaves_code_intelligence_to_its_language(environment):
    assert attempt_status(environment, None, None).no_code_intelligence is None


def test_before_any_submission_the_next_step_is_testing(environment):
    assert attempt_status(environment, None, None).next_step == "cstudy test --watch"


def test_after_a_submission_the_next_step_is_passing_the_unlocked_level(environment):
    submission(environment, LevelTally(1, 1, 1, 2, 1))
    assert attempt_status(environment, None, None).next_step == (
        "cstudy submit once level 1 passes"
    )


def test_after_the_full_pass_the_next_step_is_done(environment):
    found = environment.progress.active_attempt()
    environment.progress.update_attempt(replace(found, first_pass_at=LATER))
    submission(environment, LevelTally(1, 1, 1, 2, 2), LevelTally(2, 1, 1, 2, 2))
    assert attempt_status(environment, None, None).next_step == (
        "cstudy done --rating easy|ok|hard"
    )


def test_status_shows_the_latest_test_run(environment):
    run = RunRecord(attempt_id(environment), LATER, "abc", Tally(total=4, passed=3), 700)
    environment.progress.add_test_run(run)
    assert attempt_status(environment, None, None).last_test_run == run


def add_test_run(environment: Environment, minutes: int) -> None:
    ran_at = NOW + timedelta(minutes=minutes)
    run = RunRecord(attempt_id(environment), ran_at, "abc", Tally(total=2, passed=2), 700)
    environment.progress.add_test_run(run)


def test_a_test_run_before_a_level_opened_did_not_cover_that_level(environment):
    add_test_run(environment, minutes=10)
    open_level_2(environment)
    assert attempt_status(environment, None, None).test_run_predates_level == 2


def test_a_test_run_after_every_unlock_covers_every_open_level(environment):
    open_level_2(environment)
    add_test_run(environment, minutes=31)
    assert attempt_status(environment, None, None).test_run_predates_level is None


def test_without_a_test_run_no_level_is_left_out_of_one(environment):
    open_level_2(environment)
    assert attempt_status(environment, None, None).test_run_predates_level is None


def test_status_shows_the_latest_submission(environment):
    submission(environment, LevelTally(1, 1, 1, 2, 2), minutes=1)
    latest = submission(environment, LevelTally(1, 1, 1, 2, 1), minutes=2)
    assert project_of(environment).latest_submission == latest


def test_status_keeps_the_best_count_of_each_level(environment):
    submission(environment, LevelTally(1, 1, 1, 2, 2), minutes=1)
    submission(environment, LevelTally(1, 1, 1, 2, 1), minutes=2)
    assert project_of(environment).best_per_level == (LevelTally(1, 1, 1, 2, 2),)


def test_status_reads_the_clock(environment):
    assert attempt_status(environment, None, None).now == NOW


# files (docs/specs/cli.md#cstudy-status)


def edit_the_folder(environment: Environment) -> None:
    """Changes the README, adds a module and deletes pyproject.toml."""
    workspace = environment.workspace
    workspace.write_text(f"{PROJECT_FOLDER}/README.md", "# mine\n")
    workspace.write_text(f"{PROJECT_FOLDER}/bank/ledger.py", "LEDGER = []\n")
    workspace.absolute(f"{PROJECT_FOLDER}/pyproject.toml").unlink()


def states(environment: Environment) -> dict[str, FileState]:
    return {file.path: file.state for file in project_of(environment).files}


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
    assert project_of(environment).starter_changes == StarterChanges(
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
    attempt_status(environment, None, None)
    assert not environment.workspace.exists(f".cs/projects/{PROJECT_SLUG}.json")
