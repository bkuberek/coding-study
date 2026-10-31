"""`cstudy start` on a project problem (docs/specs/cli.md#cstudy-start): the folder, level 1's
test file, the statement and the attempt."""

from dataclasses import replace
from datetime import timedelta

import pytest

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.application.environment import Environment
from coding_study.application.project_tests import LevelTestFile
from coding_study.application.start_attempt import StartedAttempt, StartRequest, start_attempt
from coding_study.domain.attempts import AttemptStatus, Grade
from coding_study.domain.config import Config
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.domain.submissions import LevelUnlock
from tests.fakes import NOW, FakeToolchains, make_environment, repository_root
from tests.helpers import PROJECT_PROBLEMS

SLUG = "bank-project-python"
FOLDER = f"projects/{SLUG}"
LEVEL_1_TESTS = f"{FOLDER}/tests/test_level_1.py"
LEVEL_2_TESTS = f"{FOLDER}/tests/test_level_2.py"
ENTRY = f"{FOLDER}/bank/bank.py"
STATEMENT = f".statements/{SLUG}.md"


@pytest.fixture
def environment(tmp_path) -> Environment:
    toolchains = FakeToolchains(project_test_generators={Language.PYTHON: PythonTestGenerator()})
    return make_environment(repository_root(tmp_path, PROJECT_PROBLEMS), toolchains=toolchains)


def start(environment: Environment, **fields: object) -> StartedAttempt:
    request = replace(StartRequest(SLUG), **fields)  # type: ignore[arg-type]
    return start_attempt(environment, request)


def open_level_2(environment: Environment, started: StartedAttempt) -> None:
    environment.progress.update_attempt(replace(started.attempt, level_unlocked=2))


def schedule(environment: Environment) -> None:
    entry = ScheduleEntry(SLUG, ReviewState(3, 1), NOW.date(), Grade.OK, NOW - timedelta(days=3))
    environment.progress.save_schedule_entry(entry)


def test_a_new_attempt_copies_the_starter_into_the_project_folder(environment):
    start(environment)
    assert environment.workspace.exists(ENTRY)


def test_a_new_attempt_links_the_folder_to_the_workspace_venv(environment):
    start(environment)
    assert environment.workspace.absolute(f"{FOLDER}/.venv").is_symlink()


def test_a_new_attempt_writes_level_1s_test_file(environment):
    start(environment)
    assert environment.workspace.exists(LEVEL_1_TESTS)


def test_a_new_attempt_writes_no_test_file_of_a_locked_level(environment):
    start(environment)
    assert not environment.workspace.exists(LEVEL_2_TESTS)


def test_the_attempt_points_at_the_project_folder(environment):
    assert start(environment).attempt.stub_path == FOLDER


def test_the_started_attempt_opens_the_project_folder(environment):
    assert start(environment).stub_path == FOLDER


def test_a_new_attempt_opens_level_1(environment):
    assert start(environment).attempt.level_unlocked == 1


def test_a_new_attempt_records_when_level_1_opened(environment):
    started = start(environment)
    assert environment.progress.level_unlocks(started.attempt.id) == (
        LevelUnlock(started.attempt.id, 1, NOW),
    )


def test_the_statement_shows_level_1_only(environment):
    start(environment)
    assert "Level 2 is locked" in environment.workspace.read_text(STATEMENT)


def test_the_project_names_its_entry_file_and_class(environment):
    project = start(environment).project
    assert project is not None
    assert (project.entry_file, project.entry_class) == ("bank/bank.py", "Bank")


def test_the_project_counts_the_starter_and_the_generated_tests(environment):
    project = start(environment).project
    assert project is not None
    assert project.files == 4


def test_the_project_reports_level_1s_test_file(environment):
    project = start(environment).project
    assert project is not None
    assert project.tests == LevelTestFile(1, "tests/test_level_1.py", 1, True)


def test_a_project_starts_in_its_own_language_whatever_the_default(environment):
    configured = replace(environment, config=Config(default_lang=Language.KOTLIN))
    assert start(configured).attempt.language is Language.PYTHON


def test_lang_may_repeat_the_projects_language(environment):
    assert start(environment, language=Language.PYTHON).attempt.language is Language.PYTHON


def test_another_language_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="bank-project-python is solved in python only"):
        start(environment, language=Language.TYPESCRIPT)


def test_another_language_starts_nothing(environment):
    with pytest.raises(UsageError):
        start(environment, language=Language.TYPESCRIPT)
    assert environment.progress.active_attempt() is None


def test_starting_again_resumes_the_attempt(environment):
    first = start(environment)
    assert start(environment).attempt.id == first.attempt.id


def test_a_resumed_attempt_says_so(environment):
    start(environment)
    assert start(environment).resumed


def test_a_resumed_attempt_writes_back_a_missing_test_file_of_an_unlocked_level(environment):
    open_level_2(environment, start(environment))
    start(environment)
    assert environment.workspace.exists(LEVEL_2_TESTS)


def test_a_resumed_attempt_keeps_a_test_file_you_changed(environment):
    start(environment)
    environment.workspace.write_text(LEVEL_1_TESTS, "# mine\n")
    start(environment)
    assert environment.workspace.read_text(LEVEL_1_TESTS) == "# mine\n"


def test_a_resumed_attempt_never_restores_a_starter_file_you_deleted(environment):
    start(environment)
    environment.workspace.absolute(ENTRY).unlink()
    start(environment)
    assert not environment.workspace.exists(ENTRY)


def test_a_resumed_attempt_shows_the_unlocked_levels(environment):
    open_level_2(environment, start(environment))
    start(environment)
    assert "is locked" not in environment.workspace.read_text(STATEMENT)


def test_fresh_archives_the_folder_under_the_previous_attempt(environment):
    first = start(environment)
    archive = f".archive/{SLUG}/{first.attempt.id}-python"
    assert start(environment, fresh=True).archived_to == archive


def test_fresh_copies_the_starter_again(environment):
    start(environment)
    environment.workspace.write_text(ENTRY, "mine\n")
    start(environment, fresh=True)
    assert environment.workspace.read_text(ENTRY) != "mine\n"


def test_fresh_opens_level_1_again(environment):
    open_level_2(environment, start(environment))
    assert start(environment, fresh=True).attempt.level_unlocked == 1


def test_fresh_abandons_the_previous_attempt(environment):
    start(environment)
    start(environment, fresh=True)
    first_row = environment.progress.snapshot().tables["attempts"][0]
    assert first_row["status"] == AttemptStatus.ABANDONED


def test_a_refused_archive_starts_no_attempt(environment):
    first = start(environment)
    environment.workspace.write_text(f".archive/{SLUG}/{first.attempt.id}-python/kept.py", "")
    with pytest.raises(UsageError, match="already exists"):
        start(environment, fresh=True)
    assert environment.progress.active_attempt() == first.attempt


def test_fresh_without_a_previous_attempt_archives_under_the_new_one(environment):
    environment.workspace.write_text(ENTRY, "mine\n")
    started = start(environment, fresh=True)
    assert started.archived_to == f".archive/{SLUG}/{started.attempt.id}-python"


def finish(environment: Environment, started: StartedAttempt) -> None:
    ended = replace(started.attempt, status=AttemptStatus.PASSED, ended_at=NOW, grade=Grade.OK)
    environment.progress.update_attempt(ended)
    schedule(environment)


def test_a_review_attempt_archives_the_folder(environment):
    first = start(environment)
    finish(environment, first)
    assert start(environment).archived_to == f".archive/{SLUG}/{first.attempt.id}-python"


def test_a_review_attempt_starts_at_level_1(environment):
    first = start(environment)
    open_level_2(environment, first)
    finish(environment, replace(first, attempt=replace(first.attempt, level_unlocked=2)))
    assert start(environment).attempt.level_unlocked == 1


def test_a_timer_is_recorded_as_for_every_problem(environment):
    assert start(environment, timer_s=5400).attempt.time_limit_s == 5400
