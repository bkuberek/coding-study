from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade
from coding_study.domain.config import Config
from coding_study.domain.errors import LanguageNotSetUpError, UnknownProblemError
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from tests.fakes import NOW, FakeClock, FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
STUB = "python/practice/two_sum.py"
STATEMENT = ".statements/two-sum.md"


@pytest.fixture
def environment(tmp_path: Path):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    return make_environment(root, toolchains=toolchains, clock=FakeClock())


def start(environment, **fields):
    return start_attempt(environment, StartRequest(**{"slug": "two-sum", **fields}))


def test_writes_the_stub(environment):
    start(environment)
    assert environment.workspace.read_text(STUB) == "# stub for two-sum\n"


def test_reports_the_stub_and_statement_paths(environment):
    started = start(environment)
    assert (started.stub_path, started.statement_path) == (STUB, STATEMENT)


def test_renders_the_statement(environment):
    start(environment)
    assert environment.workspace.read_text(STATEMENT).startswith("# Two Sum\n")


def test_statement_hides_hints(environment):
    start(environment)
    assert "Hint" not in environment.workspace.read_text(STATEMENT)


def test_inserts_an_attempt_in_progress(environment):
    attempt = start(environment).attempt
    assert (attempt.status, attempt.mode, attempt.started_at) == (
        AttemptStatus.IN_PROGRESS,
        AttemptMode.NEW,
        NOW,
    )


def test_attempt_records_the_stub_path(environment):
    assert start(environment).attempt.stub_path == STUB


def test_language_defaults_to_the_config(environment):
    environment = replace(environment, config=Config(default_lang=Language.KOTLIN))
    with pytest.raises(LanguageNotSetUpError, match="kotlin"):
        start(environment)


def test_timer_is_stored_on_the_attempt(environment):
    assert start(environment, timer_s=1500).attempt.time_limit_s == 1500


def test_same_language_in_progress_resumes(environment):
    first = start(environment)
    second = start(environment)
    assert (second.attempt, second.resumed) == (first.attempt, True)


def test_resume_keeps_the_edited_stub(environment):
    start(environment)
    environment.workspace.write_text(STUB, "def two_sum(): ...\n")
    start(environment)
    assert environment.workspace.read_text(STUB) == "def two_sum(): ...\n"


def test_an_existing_stub_is_kept_for_a_new_attempt(environment):
    environment.workspace.write_text(STUB, "mine\n")
    started = start(environment)
    assert (environment.workspace.read_text(STUB), started.created_stub) == ("mine\n", False)


def test_fresh_abandons_the_attempt_in_progress(environment):
    start(environment)
    start(environment, fresh=True)
    statuses = environment.progress.problem_progress()["two-sum"].attempt_statuses
    assert statuses == {AttemptStatus.ABANDONED, AttemptStatus.IN_PROGRESS}


def test_fresh_archives_the_previous_file_under_its_attempt(environment):
    first = start(environment).attempt
    environment.workspace.write_text(STUB, "mine\n")
    started = start(environment, fresh=True)
    archived = f".archive/two-sum/{first.id}-python/two_sum.py"
    assert (started.archived_to, environment.workspace.read_text(archived)) == (archived, "mine\n")


def test_fresh_writes_a_new_stub(environment):
    start(environment)
    environment.workspace.write_text(STUB, "mine\n")
    start(environment, fresh=True)
    assert environment.workspace.read_text(STUB) == "# stub for two-sum\n"


def test_fresh_records_the_archive_on_the_new_attempt(environment):
    start(environment)
    started = start(environment, fresh=True)
    assert started.attempt.archive_path == started.archived_to


def test_fresh_without_a_previous_attempt_archives_under_the_new_one(environment):
    environment.workspace.write_text(STUB, "mine\n")
    started = start(environment, fresh=True)
    archive = f".archive/two-sum/{started.attempt.id}-python"
    assert started.archived_to == f"{archive}/two_sum.py"


def schedule_two_sum(environment) -> None:
    state = ReviewState(interval_days=3, reps=1)
    entry = ScheduleEntry("two-sum", state, NOW.date(), Grade.OK, NOW - timedelta(days=3))
    environment.progress.save_schedule_entry(entry)


def test_scheduled_problem_starts_a_review(environment):
    schedule_two_sum(environment)
    assert start(environment).attempt.mode is AttemptMode.REVIEW


def test_review_archives_the_previous_file(environment):
    environment.workspace.write_text(STUB, "old solution\n")
    schedule_two_sum(environment)
    assert start(environment).archived_to is not None


def test_unknown_problem(environment):
    with pytest.raises(UnknownProblemError):
        start(environment, slug="three-sum")


def test_language_without_a_stub_generator_changes_nothing(environment):
    with pytest.raises(LanguageNotSetUpError):
        start(environment, language=Language.JAVA)
    assert environment.progress.active_attempt() is None


def test_language_without_a_stub_generator_renders_no_statement(environment):
    with pytest.raises(LanguageNotSetUpError):
        start(environment, language=Language.JAVA)
    assert not environment.workspace.exists(STATEMENT)


RUST_MANIFEST = "rust/Cargo.toml"


@pytest.fixture
def rust_environment(tmp_path: Path):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains(stub_generators={Language.RUST: FakeStubGenerator()})
    return make_environment(root, toolchains=toolchains, clock=FakeClock())


def test_a_rust_start_lists_the_problem_in_the_rust_manifest(rust_environment):
    rust_environment.workspace.write_text(RUST_MANIFEST, '[package]\nname = "practice"\n')
    start(rust_environment, language=Language.RUST)
    manifest = rust_environment.workspace.read_text(RUST_MANIFEST)
    assert '[[example]]\nname = "two_sum"\npath = "practice/two_sum.rs"\n' in manifest


def test_a_resumed_rust_attempt_lists_the_problem_too(rust_environment):
    start(rust_environment, language=Language.RUST)
    rust_environment.workspace.write_text(RUST_MANIFEST, '[package]\nname = "practice"\n')
    start(rust_environment, language=Language.RUST)
    assert 'name = "two_sum"' in rust_environment.workspace.read_text(RUST_MANIFEST)


def test_without_a_rust_manifest_none_is_created(rust_environment):
    start(rust_environment, language=Language.RUST)
    assert not rust_environment.workspace.exists(RUST_MANIFEST)
