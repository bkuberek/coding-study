"""An attempt's files for the web UI: each kind's root and scope, the tree, and reading a file
(docs/specs/web-ui.md#file-api-rules)."""

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.application.attempt_files import (
    EDITABLE_BYTES,
    AttemptFileChanges,
    SavedFile,
    StartedFile,
    attempt_tree,
    read_attempt_file,
)
from coding_study.application.attempt_status import attempt_status
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.errors import (
    AttemptEndedError,
    FileChangedError,
    FileTooLargeError,
    LockBusyError,
    PathTakenError,
    UnknownFileError,
    UsageError,
)
from coding_study.domain.file_states import FileState
from coding_study.domain.problem import Language
from coding_study.domain.project_manifest import FileOrigin, project_lock
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.racing_workspace import OutsideDeletion

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
STUB_TEXT = "# stub for two-sum\n"
JAVA_PACKAGE = "jvm/java/src/main/java/practice/two_sum"
PROJECT = f"projects/{PROJECT_SLUG}"


def practice(tmp_path: Path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    return make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))


def started(environment: Environment, language: Language | None = None) -> Attempt:
    return start_attempt(environment, StartRequest("two-sum", language)).attempt


@pytest.fixture
def python(tmp_path) -> tuple[Environment, Attempt]:
    environment = practice(tmp_path)
    return environment, started(environment, Language.PYTHON)


@pytest.fixture
def project(tmp_path) -> tuple[Environment, Attempt]:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    return environment, start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt


def pair(started_attempt: tuple[Environment, Attempt]) -> tuple[Environment, Attempt]:
    """A fixture's environment and attempt, typed for unpacking into a call."""
    return started_attempt


def write(environment: Environment, path: str, content: bytes) -> None:
    target = environment.workspace.absolute(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def tree_rows(environment: Environment, attempt: Attempt) -> list[tuple[str, str, int | None]]:
    tree = attempt_tree(environment, attempt)
    return [(found.path, found.origin, found.size) for found in tree.files]


# roots and scopes


def test_a_python_attempts_root_is_the_directory_of_its_file(python):
    assert attempt_tree(*pair(python)).root == "python/practice"


def test_a_python_attempts_scope_is_its_file_only(python):
    environment, attempt = python
    write(environment, "python/practice/other.py", b"x = 1\n")
    assert tree_rows(environment, attempt) == [("two_sum.py", StartedFile.STUB, len(STUB_TEXT))]


def test_a_java_attempts_root_is_the_problems_package(tmp_path):
    environment = practice(tmp_path)
    assert attempt_tree(environment, started(environment, Language.JAVA)).root == JAVA_PACKAGE


def test_a_java_attempts_scope_is_every_java_file_in_its_package(tmp_path):
    environment = practice(tmp_path)
    attempt = started(environment, Language.JAVA)
    write(environment, f"{JAVA_PACKAGE}/Helper.java", b"class Helper {}\n")
    write(environment, f"{JAVA_PACKAGE}/notes.txt", b"thoughts\n")
    write(environment, f"{JAVA_PACKAGE}/inner/Deep.java", b"class Deep {}\n")
    assert [(path, origin) for path, origin, _size in tree_rows(environment, attempt)] == [
        ("Helper.java", FileOrigin.YOURS),
        ("Solution.java", StartedFile.STUB),
    ]


def test_an_items_scope_is_its_notes_file(tmp_path):
    environment = practice(tmp_path)
    attempt = start_item_attempt(environment, ItemStartRequest("url-shortener")).attempt
    tree = attempt_tree(environment, attempt)
    assert (tree.root, [(found.path, found.origin) for found in tree.files]) == (
        "notes/system-design",
        [("url-shortener.md", StartedFile.NOTES)],
    )


def test_a_projects_root_is_its_folder(project):
    assert attempt_tree(*pair(project)).root == PROJECT


def test_a_projects_tree_is_the_files_status_lists(project):
    environment, attempt = project
    write(environment, f"{PROJECT}/bank/ledger.py", b"LEDGER = []\n")
    status = attempt_status(environment, attempt.slug, attempt.language)
    assert status.project is not None
    tree = attempt_tree(environment, attempt)
    assert [(found.path, found.origin, found.level, found.state) for found in tree.files] == [
        (file.path, file.origin, file.level, file.state) for file in status.project.files
    ]


def test_a_projects_tree_gives_each_files_size(project):
    environment, attempt = project
    write(environment, f"{PROJECT}/bank/ledger.py", b"LEDGER = []\n")
    sizes = {found.path: found.size for found in attempt_tree(environment, attempt).files}
    assert sizes["bank/ledger.py"] == len(b"LEDGER = []\n")


def test_a_deleted_starter_file_has_no_size_and_is_not_editable(project):
    environment, attempt = project
    environment.workspace.absolute(f"{PROJECT}/README.md").unlink()
    deleted = next(
        found for found in attempt_tree(environment, attempt).files if found.path == "README.md"
    )
    assert (deleted.state, deleted.size, deleted.editable) == (FileState.DELETED, None, False)


def test_the_tree_never_lists_a_file_a_tool_wrote(project):
    environment, attempt = project
    write(environment, f"{PROJECT}/.pytest_cache/v/cache", b"{}")
    paths = [found.path for found in attempt_tree(environment, attempt).files]
    assert not any(path.startswith(".pytest_cache") for path in paths)


# reading


def test_reading_the_stub_gives_its_text(python):
    assert read_attempt_file(*pair(python), "two_sum.py").text == STUB_TEXT


def test_reading_a_file_gives_the_sha256_of_its_bytes(python):
    expected = hashlib.sha256(STUB_TEXT.encode()).hexdigest()
    assert read_attempt_file(*pair(python), "two_sum.py").sha256 == expected


def test_a_utf8_file_up_to_the_limit_is_editable(python):
    environment, attempt = python
    write(environment, "python/practice/two_sum.py", b"#" * EDITABLE_BYTES)
    assert read_attempt_file(environment, attempt, "two_sum.py").editable


def test_a_file_over_the_limit_is_read_only_without_text(python):
    environment, attempt = python
    write(environment, "python/practice/two_sum.py", b"#" * (EDITABLE_BYTES + 1))
    content = read_attempt_file(environment, attempt, "two_sum.py")
    assert (content.text, content.editable) == (None, False)


def test_a_file_that_is_not_utf8_is_read_only_without_text(python):
    environment, attempt = python
    write(environment, "python/practice/two_sum.py", b"\xff\xfe binary")
    content = read_attempt_file(environment, attempt, "two_sum.py")
    assert (content.text, content.editable) == (None, False)


def test_a_path_is_read_once_its_dot_segments_resolve(python):
    assert read_attempt_file(*pair(python), "./x/../two_sum.py").file.path == "two_sum.py"


def test_a_file_outside_a_single_file_scope_is_refused(python):
    environment, attempt = python
    write(environment, "python/practice/other.py", b"x = 1\n")
    with pytest.raises(UsageError, match=r"cannot read other\.py: not one of the attempt's files"):
        read_attempt_file(environment, attempt, "other.py")


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ("../pyproject.toml", "leaves the folder"),
        ("/etc/hosts", "is absolute"),
        ("bank\\bank.py", "uses \\\\ instead of /"),
    ],
)
def test_a_path_the_folder_rules_refuse_is_refused_with_their_reason(project, path, reason):
    with pytest.raises(UsageError, match=f"cannot read .*: {reason}"):
        read_attempt_file(*pair(project), path)


def test_a_file_a_tool_wrote_is_refused(project):
    with pytest.raises(UsageError, match=r"cannot read \.venv/bin/python: the page never shows"):
        read_attempt_file(*pair(project), ".venv/bin/python")


def test_a_link_is_refused(project):
    environment, attempt = project
    write(environment, "secret.txt", b"secret\n")
    environment.workspace.absolute(f"{PROJECT}/README.md").unlink()
    environment.workspace.absolute(f"{PROJECT}/README.md").symlink_to("../../secret.txt")
    with pytest.raises(UsageError, match=r"README\.md is a symbolic link"):
        read_attempt_file(environment, attempt, "README.md")


def test_a_missing_file_in_a_project_is_unknown(project):
    with pytest.raises(UnknownFileError, match=f"no file bank/ledger.py in {PROJECT}"):
        read_attempt_file(*pair(project), "bank/ledger.py")


def test_a_project_file_you_added_reads_as_yours(project):
    environment, attempt = project
    write(environment, f"{PROJECT}/bank/ledger.py", b"LEDGER = []\n")
    found = read_attempt_file(environment, attempt, "bank/ledger.py").file
    assert (found.origin, found.state) == (FileOrigin.YOURS, FileState.ADDED)


def test_a_starter_file_reads_with_its_state(project):
    environment, attempt = project
    write(environment, f"{PROJECT}/README.md", b"# Mine\n")
    found = read_attempt_file(environment, attempt, "README.md").file
    assert (found.origin, found.state) == (FileOrigin.STARTER, FileState.MODIFIED)


# changes: each waits at most a deadline for the project's lock

DEADLINE_S = 0.05
SAVED = "class Bank:\n    pass\n"


def changes(started_attempt: tuple[Environment, Attempt]) -> AttemptFileChanges:
    environment, attempt = started_attempt
    return AttemptFileChanges(environment, attempt, DEADLINE_S)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def current_sha(started_attempt: tuple[Environment, Attempt], path: str) -> str:
    return read_attempt_file(*pair(started_attempt), path).sha256


def on_disk(started_attempt: tuple[Environment, Attempt], path: str) -> str:
    environment, _attempt = started_attempt
    return environment.workspace.read_text(path)


@pytest.fixture
def held_lock(project):
    """Another `cstudy` holding the project's lock."""
    environment, _attempt = project
    with exclusive_lock(environment.workspace.absolute(project_lock(PROJECT_SLUG))):
        yield


# saving


def test_saving_writes_the_text(project):
    changes(project).save("bank/bank.py", SAVED, current_sha(project, "bank/bank.py"))
    assert on_disk(project, f"{PROJECT}/bank/bank.py") == SAVED


def test_saving_answers_the_cleaned_path_and_the_new_sha256(project):
    saved = changes(project).save("./bank/bank.py", SAVED, current_sha(project, "bank/bank.py"))
    assert saved == SavedFile("bank/bank.py", sha(SAVED))


def test_a_saved_starter_file_turns_modified(project):
    changes(project).save("README.md", "# Mine\n", current_sha(project, "README.md"))
    assert read_attempt_file(*pair(project), "README.md").file.state is FileState.MODIFIED


def test_saving_the_file_a_single_file_attempt_started_with(python):
    changes(python).save("two_sum.py", SAVED, sha(STUB_TEXT))
    assert on_disk(python, "python/practice/two_sum.py") == SAVED


def test_saving_an_items_notes(tmp_path):
    environment = practice(tmp_path)
    attempt = start_item_attempt(environment, ItemStartRequest("url-shortener")).attempt
    notes = read_attempt_file(environment, attempt, "url-shortener.md")
    changes((environment, attempt)).save("url-shortener.md", "# My design\n", notes.sha256)
    assert environment.workspace.read_text("notes/system-design/url-shortener.md") == (
        "# My design\n"
    )


def test_saving_over_a_file_that_changed_since_it_was_read_is_refused(project):
    environment, _attempt = project
    stale = current_sha(project, "README.md")
    write(environment, f"{PROJECT}/README.md", b"# Theirs\n")
    with pytest.raises(FileChangedError, match=r"README\.md changed since"):
        changes(project).save("README.md", "# Mine\n", stale)


def test_a_refused_save_names_the_files_current_sha256(project):
    environment, _attempt = project
    stale = current_sha(project, "README.md")
    write(environment, f"{PROJECT}/README.md", b"# Theirs\n")
    with pytest.raises(FileChangedError) as refused:
        changes(project).save("README.md", "# Mine\n", stale)
    assert refused.value.sha256 == sha("# Theirs\n")


def test_a_refused_save_leaves_the_file_alone(project):
    environment, _attempt = project
    stale = current_sha(project, "README.md")
    write(environment, f"{PROJECT}/README.md", b"# Theirs\n")
    with pytest.raises(FileChangedError):
        changes(project).save("README.md", "# Mine\n", stale)
    assert on_disk(project, f"{PROJECT}/README.md") == "# Theirs\n"


def test_saving_a_file_deleted_since_it_was_read_is_refused_without_a_sha256(project):
    environment, _attempt = project
    stale = current_sha(project, "README.md")
    environment.workspace.absolute(f"{PROJECT}/README.md").unlink()
    with pytest.raises(FileChangedError, match=r"README\.md was deleted since") as refused:
        changes(project).save("README.md", "# Mine\n", stale)
    assert refused.value.sha256 is None


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ("../pyproject.toml", "leaves the folder"),
        ("bank/../../x.py", "leaves the folder"),
        ("/etc/hosts", "is absolute"),
        ("bank\\bank.py", "uses \\\\ instead of /"),
        (".venv/bin/python", "the page never shows what tools write"),
    ],
)
def test_saving_a_path_the_rules_refuse_is_refused_with_their_reason(project, path, reason):
    with pytest.raises(UsageError, match=f"cannot save .*: {reason}"):
        changes(project).save(path, SAVED, "unused")


def test_saving_through_a_link_is_refused(project):
    environment, _attempt = project
    write(environment, "secret.txt", b"secret\n")
    environment.workspace.absolute(f"{PROJECT}/README.md").unlink()
    environment.workspace.absolute(f"{PROJECT}/README.md").symlink_to("../../secret.txt")
    with pytest.raises(UsageError, match=r"cannot save README\.md: README\.md is a symbolic link"):
        changes(project).save("README.md", "# Mine\n", sha("secret\n"))


def test_saving_through_a_link_leaves_its_target_alone(project):
    environment, _attempt = project
    write(environment, "secret.txt", b"secret\n")
    environment.workspace.absolute(f"{PROJECT}/README.md").unlink()
    environment.workspace.absolute(f"{PROJECT}/README.md").symlink_to("../../secret.txt")
    with pytest.raises(UsageError):
        changes(project).save("README.md", "# Mine\n", sha("secret\n"))
    assert on_disk(project, "secret.txt") == "secret\n"


def test_saving_a_file_outside_a_single_file_scope_is_refused(python):
    environment, _attempt = python
    write(environment, "python/practice/other.py", b"x = 1\n")
    with pytest.raises(UsageError, match=r"cannot save other\.py: not one of the attempt's files"):
        changes(python).save("other.py", SAVED, sha("x = 1\n"))


def test_saving_text_over_the_limit_is_refused(python):
    with pytest.raises(FileTooLargeError, match=r"cannot save two_sum\.py: .* over 1 MiB"):
        changes(python).save("two_sum.py", "#" * (EDITABLE_BYTES + 1), sha(STUB_TEXT))


def test_saving_text_up_to_the_limit_is_kept(python):
    changes(python).save("two_sum.py", "#" * EDITABLE_BYTES, sha(STUB_TEXT))
    assert len(on_disk(python, "python/practice/two_sum.py")) == EDITABLE_BYTES


def test_saving_over_a_file_that_is_not_text_is_refused(python):
    environment, _attempt = python
    write(environment, "python/practice/two_sum.py", b"\xff\xfe binary")
    current = hashlib.sha256(b"\xff\xfe binary").hexdigest()
    with pytest.raises(UsageError, match=r"cannot save two_sum\.py: it is not UTF-8 text"):
        changes(python).save("two_sum.py", SAVED, current)


def test_saving_waits_at_most_the_deadline_for_the_projects_lock(project, held_lock):
    with pytest.raises(LockBusyError):
        changes(project).save("README.md", "# Mine\n", current_sha(project, "README.md"))


def test_saving_for_an_attempt_that_ended_is_refused(project):
    environment, attempt = project
    expected = current_sha(project, "README.md")
    environment.progress.update_attempt(replace(attempt, status=AttemptStatus.ABANDONED))
    with pytest.raises(AttemptEndedError):
        changes(project).save("README.md", "# Mine\n", expected)


# creating


def test_creating_writes_a_new_file(project):
    changes(project).create("bank/ledger.py", "LEDGER = []\n")
    assert on_disk(project, f"{PROJECT}/bank/ledger.py") == "LEDGER = []\n"


def test_creating_answers_the_new_files_sha256(project):
    created = changes(project).create("bank/ledger.py", "LEDGER = []\n")
    assert created == SavedFile("bank/ledger.py", sha("LEDGER = []\n"))


def test_creating_makes_the_folders_on_the_way(project):
    changes(project).create("bank/models/account.py", "class Account: ...\n")
    assert on_disk(project, f"{PROJECT}/bank/models/account.py") == "class Account: ...\n"


def test_a_created_project_file_reads_as_yours_and_added(project):
    changes(project).create("bank/ledger.py", "LEDGER = []\n")
    found = read_attempt_file(*pair(project), "bank/ledger.py").file
    assert (found.origin, found.state) == (FileOrigin.YOURS, FileState.ADDED)


def test_creating_a_file_that_exists_is_refused_with_its_sha256(project):
    with pytest.raises(FileChangedError, match=r"cannot create README\.md: it exists") as refused:
        changes(project).create("README.md", "# Mine\n")
    assert refused.value.sha256 == current_sha(project, "README.md")


def test_creating_where_a_folder_is_is_refused(project):
    with pytest.raises(UsageError, match="cannot create bank: bank is a directory"):
        changes(project).create("bank", "x\n")


def test_creating_a_file_a_tool_would_write_is_refused(project):
    with pytest.raises(UsageError, match=r"cannot create node_modules/x\.js: the page never shows"):
        changes(project).create("node_modules/x.js", "x\n")


def test_creating_a_java_file_in_a_java_attempts_package(tmp_path):
    environment = practice(tmp_path)
    attempt = started(environment, Language.JAVA)
    changes((environment, attempt)).create("Helper.java", "class Helper {}\n")
    assert environment.workspace.read_text(f"{JAVA_PACKAGE}/Helper.java") == "class Helper {}\n"


@pytest.mark.parametrize("path", ["inner/Deep.java", "notes.txt"])
def test_creating_anything_else_in_a_java_package_is_refused(tmp_path, path):
    environment = practice(tmp_path)
    attempt = started(environment, Language.JAVA)
    with pytest.raises(UsageError, match=r"not one of the attempt's \.java files"):
        changes((environment, attempt)).create(path, "x\n")


def test_creating_beside_a_single_file_attempts_file_is_refused(python):
    with pytest.raises(UsageError, match=r"cannot create helper\.py: .* one file, two_sum\.py"):
        changes(python).create("helper.py", "x = 1\n")


def test_creating_waits_at_most_the_deadline_for_the_projects_lock(project, held_lock):
    with pytest.raises(LockBusyError):
        changes(project).create("bank/ledger.py", "LEDGER = []\n")


# moving

README_TEXT = "# Bank Project (Python)"


def state_of(started_attempt: tuple[Environment, Attempt], path: str) -> FileState | None:
    tree = attempt_tree(*pair(started_attempt))
    return next(found.state for found in tree.files if found.path == path)


def test_moving_puts_the_file_at_its_new_path(project):
    expected = on_disk(project, f"{PROJECT}/README.md")
    changes(project).move("README.md", "docs/README.md", current_sha(project, "README.md"))
    assert on_disk(project, f"{PROJECT}/docs/README.md") == expected


def test_moving_answers_the_new_path_and_the_files_sha256(project):
    expected = current_sha(project, "README.md")
    moved = changes(project).move("README.md", "./docs/README.md", expected)
    assert moved == SavedFile("docs/README.md", expected)


def test_a_moved_starter_file_shows_deleted_at_its_old_path(project):
    changes(project).move("README.md", "NOTES.md", current_sha(project, "README.md"))
    assert (state_of(project, "README.md"), state_of(project, "NOTES.md")) == (
        FileState.DELETED,
        FileState.ADDED,
    )


def test_moving_a_file_that_changed_since_it_was_read_is_refused(project):
    environment, _attempt = project
    stale = current_sha(project, "README.md")
    write(environment, f"{PROJECT}/README.md", b"# Theirs\n")
    with pytest.raises(FileChangedError, match=r"README\.md changed since"):
        changes(project).move("README.md", "NOTES.md", stale)


def test_moving_onto_a_file_is_refused(project):
    with pytest.raises(PathTakenError, match=r"cannot move README\.md to bank/bank\.py: it exists"):
        changes(project).move("README.md", "bank/bank.py", current_sha(project, "README.md"))


def test_moving_onto_a_file_leaves_both_alone(project):
    expected = on_disk(project, f"{PROJECT}/bank/bank.py")
    with pytest.raises(PathTakenError):
        changes(project).move("README.md", "bank/bank.py", current_sha(project, "README.md"))
    assert on_disk(project, f"{PROJECT}/bank/bank.py") == expected


def test_moving_a_file_to_its_own_path_is_refused(project):
    with pytest.raises(UsageError, match=r"cannot move README\.md: it is already there"):
        changes(project).move("README.md", "./README.md", current_sha(project, "README.md"))


@pytest.mark.parametrize(
    ("target", "reason"),
    [
        ("../README.md", "leaves the folder"),
        ("/tmp/README.md", "is absolute"),
        (".venv/README.md", "the page never shows what tools write"),
    ],
)
def test_moving_to_a_path_the_rules_refuse_is_refused(project, target, reason):
    with pytest.raises(UsageError, match=f"cannot move a file to .*: {reason}"):
        changes(project).move("README.md", target, current_sha(project, "README.md"))


def test_moving_into_a_directory_that_is_a_link_is_refused(project):
    environment, _attempt = project
    write(environment, "elsewhere/kept.py", b"kept\n")
    environment.workspace.absolute(f"{PROJECT}/out").symlink_to(
        "../../elsewhere", target_is_directory=True
    )
    with pytest.raises(UsageError, match=r"cannot move README\.md: out is a symbolic link"):
        changes(project).move("README.md", "out/README.md", current_sha(project, "README.md"))


def test_moving_a_java_file_within_its_package(tmp_path):
    environment = practice(tmp_path)
    attempt = started(environment, Language.JAVA)
    write(environment, f"{JAVA_PACKAGE}/Helper.java", b"class Helper {}\n")
    expected = hashlib.sha256(b"class Helper {}\n").hexdigest()
    changes((environment, attempt)).move("Helper.java", "Helpers.java", expected)
    assert environment.workspace.read_text(f"{JAVA_PACKAGE}/Helpers.java") == "class Helper {}\n"


def test_moving_a_java_file_out_of_its_package_is_refused(tmp_path):
    environment = practice(tmp_path)
    attempt = started(environment, Language.JAVA)
    write(environment, f"{JAVA_PACKAGE}/Helper.java", b"class Helper {}\n")
    expected = hashlib.sha256(b"class Helper {}\n").hexdigest()
    with pytest.raises(UsageError, match=r"not one of the attempt's \.java files"):
        changes((environment, attempt)).move("Helper.java", "inner/Helper.java", expected)


def test_moving_a_single_file_attempts_file_is_refused(python):
    with pytest.raises(UsageError, match=r"cannot move two_sum\.py: the attempt has one file"):
        changes(python).move("two_sum.py", "solution.py", sha(STUB_TEXT))


def losing_a_race(started_attempt: tuple[Environment, Attempt]) -> AttemptFileChanges:
    """Changes whose file another program deletes once they checked its content."""
    environment, attempt = started_attempt
    racing = replace(environment, workspace=OutsideDeletion(environment.root))
    return AttemptFileChanges(racing, attempt, DEADLINE_S)


def test_moving_a_file_deleted_on_the_way_is_refused_without_a_sha256(project):
    expected = current_sha(project, "README.md")
    with pytest.raises(FileChangedError) as refused:
        losing_a_race(project).move("README.md", "NOTES.md", expected)
    assert refused.value.sha256 is None


def test_moving_waits_at_most_the_deadline_for_the_projects_lock(project, held_lock):
    with pytest.raises(LockBusyError):
        changes(project).move("README.md", "NOTES.md", current_sha(project, "README.md"))


# deleting


def test_deleting_removes_the_file(project):
    environment, _attempt = project
    changes(project).delete("bank/bank.py", current_sha(project, "bank/bank.py"))
    assert not environment.workspace.exists(f"{PROJECT}/bank/bank.py")


def test_a_deleted_starter_file_shows_deleted(project):
    changes(project).delete("README.md", current_sha(project, "README.md"))
    assert state_of(project, "README.md") is FileState.DELETED


def test_deleting_a_file_that_changed_since_it_was_read_is_refused(project):
    environment, _attempt = project
    stale = current_sha(project, "README.md")
    write(environment, f"{PROJECT}/README.md", b"# Theirs\n")
    with pytest.raises(FileChangedError, match=r"README\.md changed since"):
        changes(project).delete("README.md", stale)


def test_deleting_a_file_already_gone_is_refused_without_a_sha256(project):
    environment, _attempt = project
    stale = current_sha(project, "README.md")
    environment.workspace.absolute(f"{PROJECT}/README.md").unlink()
    with pytest.raises(FileChangedError) as refused:
        changes(project).delete("README.md", stale)
    assert refused.value.sha256 is None


def test_deleting_a_file_deleted_on_the_way_is_refused_without_a_sha256(project):
    expected = current_sha(project, "README.md")
    with pytest.raises(FileChangedError) as refused:
        losing_a_race(project).delete("README.md", expected)
    assert refused.value.sha256 is None


def test_deleting_a_link_is_refused(project):
    environment, _attempt = project
    write(environment, "secret.txt", b"secret\n")
    environment.workspace.absolute(f"{PROJECT}/README.md").unlink()
    environment.workspace.absolute(f"{PROJECT}/README.md").symlink_to("../../secret.txt")
    with pytest.raises(UsageError, match=r"README\.md is a symbolic link"):
        changes(project).delete("README.md", sha("secret\n"))


def test_deleting_a_single_file_attempts_file_is_refused(python):
    with pytest.raises(UsageError, match=r"cannot delete two_sum\.py: the attempt has one file"):
        changes(python).delete("two_sum.py", sha(STUB_TEXT))


def test_deleting_a_java_file_of_the_package(tmp_path):
    environment = practice(tmp_path)
    attempt = started(environment, Language.JAVA)
    write(environment, f"{JAVA_PACKAGE}/Helper.java", b"class Helper {}\n")
    expected = hashlib.sha256(b"class Helper {}\n").hexdigest()
    changes((environment, attempt)).delete("Helper.java", expected)
    assert not environment.workspace.exists(f"{JAVA_PACKAGE}/Helper.java")


def test_deleting_waits_at_most_the_deadline_for_the_projects_lock(project, held_lock):
    with pytest.raises(LockBusyError):
        changes(project).delete("README.md", current_sha(project, "README.md"))


# restoring, as `cstudy start --restore` does


def test_restoring_a_modified_starter_file_turns_it_unchanged(project):
    environment, _attempt = project
    write(environment, f"{PROJECT}/README.md", b"# Mine\n")
    changes(project).restore("README.md")
    assert state_of(project, "README.md") is FileState.UNCHANGED


def test_restoring_a_deleted_starter_file_writes_it_back(project):
    environment, _attempt = project
    environment.workspace.absolute(f"{PROJECT}/README.md").unlink()
    changes(project).restore("README.md")
    assert on_disk(project, f"{PROJECT}/README.md").startswith(README_TEXT)


def test_restoring_answers_the_files_origin(project):
    restored = changes(project).restore("./README.md")
    assert (restored.path, restored.origin, restored.level) == (
        "README.md",
        FileOrigin.STARTER,
        None,
    )


def test_restoring_a_file_you_added_is_refused(project):
    environment, _attempt = project
    write(environment, f"{PROJECT}/bank/ledger.py", b"LEDGER = []\n")
    with pytest.raises(UsageError, match=r"cannot restore bank/ledger\.py: not a starter file"):
        changes(project).restore("bank/ledger.py")


def test_restoring_in_a_single_file_attempt_is_refused_as_the_cli_refuses(python):
    with pytest.raises(UsageError, match="--restore is for project problems"):
        changes(python).restore("two_sum.py")


def test_restoring_waits_at_most_the_deadline_for_the_projects_lock(project, held_lock):
    with pytest.raises(LockBusyError):
        changes(project).restore("README.md")
