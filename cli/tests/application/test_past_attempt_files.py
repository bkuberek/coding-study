"""The files of a past attempt, read-only (docs/specs/web-ui.md#past-attempt-files): from the
archive folder the next start moved them to, else for the latest attempt of a problem and language
from the files as they are now, else not available."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.attempt_files import EDITABLE_BYTES
from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.environment import Environment
from coding_study.application.past_attempt_files import (
    FilesSource,
    PastEntry,
    PastFiles,
    past_attempt_files,
    read_past_file,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus, Rating
from coding_study.domain.errors import UnknownAttemptError, UnknownFileError, UsageError
from coding_study.domain.problem import Language
from coding_study.domain.workspace_projects import is_untracked
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
STUB_TEXT = "# stub for two-sum\n"
STUB = "python/practice/two_sum.py"
NOTES = "notes/system-design/url-shortener.md"
PROJECT = f"projects/{PROJECT_SLUG}"
ENTRY = "bank/bank.py"
SOLVED = "def two_sum(): return [0, 1]\n"


@pytest.fixture
def environment(tmp_path: Path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    return make_environment(root, toolchains=toolchains)


@pytest.fixture
def project(tmp_path: Path) -> Environment:
    return project_environment(tmp_path, ScriptedProjectProcess())


def start(environment: Environment, **fields: object) -> Attempt:
    request = StartRequest("two-sum", Language.PYTHON, **fields)  # type: ignore[arg-type]
    return start_attempt(environment, request).attempt


def solved(environment: Environment, text: str = SOLVED) -> Attempt:
    """The attempt in progress, its file written, finished with Done."""
    attempt = start(environment)
    environment.workspace.write_text(STUB, text)
    complete_attempt(environment, DoneRequest(gave_up=True))
    return attempt


def abandoned(environment: Environment) -> Attempt:
    attempt = start(environment)
    ended = replace(attempt, status=AttemptStatus.ABANDONED, ended_at=attempt.started_at)
    environment.progress.update_attempt(ended)
    return ended


def files_of(environment: Environment, attempt: Attempt) -> PastFiles:
    return past_attempt_files(environment, attempt.id)


def paths(files: PastFiles) -> list[str]:
    return [entry.path for entry in files.entries]


# the latest attempt: the files as they are now


def test_the_latest_attempts_files_are_the_current_ones(environment):
    attempt = solved(environment)
    assert files_of(environment, attempt) == PastFiles(
        FilesSource.CURRENT, "python/practice", (PastEntry("two_sum.py", len(SOLVED)),)
    )


def test_a_current_file_reads_as_it_is_now(environment):
    attempt = solved(environment)
    environment.workspace.write_text(STUB, "edited since\n")
    read = read_past_file(environment, attempt.id, "two_sum.py")
    assert (read.source, read.content.text) == (FilesSource.CURRENT, "edited since\n")


def test_a_deleted_file_of_the_latest_attempt_leaves_nothing_to_show(environment):
    attempt = solved(environment)
    environment.workspace.absolute(STUB).unlink()
    assert files_of(environment, attempt) == PastFiles(FilesSource.MISSING, None, ())


def test_an_abandoned_latest_attempt_shows_its_current_files(environment):
    attempt = abandoned(environment)
    assert files_of(environment, attempt).source is FilesSource.CURRENT


# an older attempt: the archive the next start made


def test_a_review_start_moves_the_files_to_the_archive_the_first_attempt_reads_from(environment):
    first = solved(environment)
    start(environment)
    assert files_of(environment, first) == PastFiles(
        FilesSource.ARCHIVE,
        f".archive/two-sum/{first.id}-python",
        (PastEntry("two_sum.py", len(SOLVED)),),
    )


def test_an_archived_file_reads_as_it_was_when_the_next_attempt_started(environment):
    first = solved(environment)
    start(environment)
    read = read_past_file(environment, first.id, "two_sum.py")
    assert (read.source, read.content.text) == (FilesSource.ARCHIVE, SOLVED)


def test_a_fresh_start_archives_the_abandoned_attempts_files(environment):
    first = start(environment)
    environment.workspace.write_text(STUB, SOLVED)
    start(environment, fresh=True)
    assert files_of(environment, first).source is FilesSource.ARCHIVE


def test_after_a_second_attempt_each_reads_from_its_own_place(environment):
    first = solved(environment, "first\n")
    second = solved(environment, "second\n")
    texts = {
        attempt.id: read_past_file(environment, attempt.id, "two_sum.py").content.text
        for attempt in (first, second)
    }
    assert texts == {first.id: "first\n", second.id: "second\n"}


def test_the_archive_shows_when_the_file_is_deleted_from_the_workspace(environment):
    first = solved(environment)
    start(environment)
    environment.workspace.absolute(STUB).unlink()
    assert files_of(environment, first).source is FilesSource.ARCHIVE


# an older attempt whose files were never archived


def test_an_older_attempt_that_was_never_archived_has_no_files(environment):
    first = abandoned(environment)
    solved(environment)
    assert files_of(environment, first) == PastFiles(FilesSource.MISSING, None, ())


def test_an_archive_folder_without_a_file_is_no_files(environment):
    first = abandoned(environment)
    solved(environment)
    environment.workspace.absolute(f".archive/two-sum/{first.id}-python").mkdir(parents=True)
    assert files_of(environment, first).source is FilesSource.MISSING


def test_the_files_of_a_missing_source_read_as_not_found(environment):
    first = abandoned(environment)
    solved(environment)
    with pytest.raises(UnknownFileError):
        read_past_file(environment, first.id, "two_sum.py")


# a file archived before any attempt wrote one


def test_a_file_archived_under_the_first_attempt_is_not_that_attempts_work(environment):
    environment.workspace.write_text(STUB, "written before any attempt\n")
    first = start(environment, fresh=True)
    complete_attempt(environment, DoneRequest(gave_up=True))
    assert files_of(environment, first) == PastFiles(
        FilesSource.CURRENT, "python/practice", (PastEntry("two_sum.py", len(STUB_TEXT)),)
    )


# who may be read


def test_an_unknown_attempt_is_unknown(environment):
    with pytest.raises(UnknownAttemptError):
        past_attempt_files(environment, 41)


def test_an_attempt_in_progress_belongs_to_the_attempt_view(environment):
    attempt = start(environment)
    with pytest.raises(UsageError, match="in progress; open it in the Attempt view"):
        files_of(environment, attempt)


def test_reading_an_attempt_in_progress_is_refused_too(environment):
    attempt = start(environment)
    with pytest.raises(UsageError, match="in progress"):
        read_past_file(environment, attempt.id, "two_sum.py")


def test_a_mock_attempt_is_an_ordinary_past_attempt(environment):
    attempt = start_attempt(
        environment, StartRequest("two-sum", Language.PYTHON, mock=True)
    ).attempt
    complete_attempt(environment, DoneRequest(gave_up=True))
    assert files_of(environment, attempt).source is FilesSource.CURRENT


# the archive's paths


@pytest.fixture
def archived(environment) -> Attempt:
    """A first attempt whose folder holds its file and some junk."""
    first = solved(environment)
    start(environment)
    folder = environment.workspace.absolute(f".archive/two-sum/{first.id}-python")
    (folder / "__pycache__").mkdir()
    (folder / "__pycache__" / "x.pyc").write_bytes(b"\0")
    return first


def test_what_tools_wrote_into_the_archive_is_not_listed(environment, archived):
    assert paths(files_of(environment, archived)) == ["two_sum.py"]


def test_a_path_that_leaves_the_archive_is_refused(environment, archived):
    with pytest.raises(UsageError, match=r"cannot read \.\./two_sum\.py: leaves the folder"):
        read_past_file(environment, archived.id, "../two_sum.py")


def test_an_absolute_path_is_refused(environment, archived):
    with pytest.raises(UsageError, match="cannot read /etc/hosts"):
        read_past_file(environment, archived.id, "/etc/hosts")


def test_a_backslash_path_is_refused(environment, archived):
    with pytest.raises(UsageError, match="cannot read"):
        read_past_file(environment, archived.id, "a\\b.py")


def test_a_tool_output_path_is_refused(environment, archived):
    with pytest.raises(UsageError, match="never shows what tools write"):
        read_past_file(environment, archived.id, "__pycache__/x.pyc")


def test_a_file_the_archive_lacks_is_not_found(environment, archived):
    with pytest.raises(UnknownFileError, match=r"no file other\.py in \.archive/two-sum/"):
        read_past_file(environment, archived.id, "other.py")


def test_a_link_in_the_archive_is_not_listed(environment, archived):
    folder = environment.workspace.absolute(f".archive/two-sum/{archived.id}-python")
    (folder / "link.py").symlink_to(folder / "two_sum.py")
    assert paths(files_of(environment, archived)) == ["two_sum.py"]


def test_a_link_in_the_archive_is_not_followed(environment, archived):
    folder = environment.workspace.absolute(f".archive/two-sum/{archived.id}-python")
    (folder / "link.py").symlink_to(folder / "two_sum.py")
    with pytest.raises(UsageError, match=r"link\.py is a symbolic link"):
        read_past_file(environment, archived.id, "link.py")


def test_a_directory_that_is_a_link_is_not_followed(environment, archived, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.py").write_text("secret\n")
    folder = environment.workspace.absolute(f".archive/two-sum/{archived.id}-python")
    (folder / "sub").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UsageError, match="sub is a symbolic link"):
        read_past_file(environment, archived.id, "sub/secret.py")


# size and text limits


def test_text_up_to_1_mib_reads_as_text(environment):
    first = solved(environment, "a" * EDITABLE_BYTES)
    start(environment)
    assert read_past_file(environment, first.id, "two_sum.py").content.text == "a" * EDITABLE_BYTES


def test_text_over_1_mib_reads_without_its_text(environment):
    first = solved(environment, "a" * (EDITABLE_BYTES + 1))
    start(environment)
    read = read_past_file(environment, first.id, "two_sum.py")
    assert (read.content.text, len(read.content.content)) == (None, EDITABLE_BYTES + 1)


def test_a_file_that_is_not_utf8_reads_without_its_text(environment):
    first = solved(environment)
    start(environment)
    folder = environment.workspace.absolute(f".archive/two-sum/{first.id}-python")
    (folder / "data.bin").write_bytes(b"\xff\xfe\x00")
    assert read_past_file(environment, first.id, "data.bin").content.text is None


def test_a_file_over_1_mib_is_still_listed_with_its_size(environment):
    first = solved(environment, "a" * (EDITABLE_BYTES + 1))
    start(environment)
    assert files_of(environment, first).entries == (PastEntry("two_sum.py", EDITABLE_BYTES + 1),)


# the current files obey the attempt's scope


def test_a_current_file_outside_the_attempts_scope_is_refused(environment):
    attempt = solved(environment)
    with pytest.raises(UsageError, match=r"cannot read other\.py: not one of the attempt's files"):
        read_past_file(environment, attempt.id, "other.py")


def test_a_current_path_that_leaves_the_root_is_refused(environment):
    attempt = solved(environment)
    with pytest.raises(UsageError, match="leaves the folder"):
        read_past_file(environment, attempt.id, "../practice/two_sum.py")


# items


def test_an_items_latest_attempt_shows_its_notes(environment):
    attempt = start_item_attempt(environment, ItemStartRequest("url-shortener")).attempt
    environment.workspace.write_text(NOTES, "my design\n")
    complete_attempt(environment, DoneRequest(rating=Rating.OK))
    assert files_of(environment, attempt) == PastFiles(
        FilesSource.CURRENT, "notes/system-design", (PastEntry("url-shortener.md", 10),)
    )


def test_a_review_start_archives_the_notes_where_the_first_attempt_reads_them(environment):
    first = start_item_attempt(environment, ItemStartRequest("url-shortener")).attempt
    environment.workspace.write_text(NOTES, "my design\n")
    complete_attempt(environment, DoneRequest(rating=Rating.OK))
    start_item_attempt(environment, ItemStartRequest("url-shortener"))
    assert files_of(environment, first) == PastFiles(
        FilesSource.ARCHIVE,
        f".archive/url-shortener/{first.id}-notes",
        (PastEntry("url-shortener.md", 10),),
    )


# projects


def test_a_projects_latest_attempt_lists_the_folder_without_what_tools_wrote(project):
    attempt = start_attempt(project, StartRequest(PROJECT_SLUG)).attempt
    project.workspace.write_text(f"{PROJECT}/__pycache__/bank.pyc", "x\n")
    complete_attempt(project, DoneRequest(gave_up=True))
    listed = paths(files_of(project, attempt))
    assert (ENTRY in listed, any(is_untracked(path) for path in listed)) == (True, False)


def test_a_projects_files_are_current_until_the_next_start_archives_the_folder(project):
    first = start_attempt(project, StartRequest(PROJECT_SLUG)).attempt
    project.workspace.write_text(f"{PROJECT}/{ENTRY}", "mine\n")
    complete_attempt(project, DoneRequest(gave_up=True))
    start_attempt(project, StartRequest(PROJECT_SLUG))
    files = files_of(project, first)
    assert (files.source, files.root) == (
        FilesSource.ARCHIVE,
        f".archive/{PROJECT_SLUG}/{first.id}-python",
    )


def test_an_archived_project_file_reads_as_the_attempt_left_it(project):
    first = start_attempt(project, StartRequest(PROJECT_SLUG)).attempt
    project.workspace.write_text(f"{PROJECT}/{ENTRY}", "mine\n")
    complete_attempt(project, DoneRequest(gave_up=True))
    start_attempt(project, StartRequest(PROJECT_SLUG))
    assert read_past_file(project, first.id, ENTRY).content.text == "mine\n"
