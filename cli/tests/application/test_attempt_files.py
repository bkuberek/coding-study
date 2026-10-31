"""An attempt's files for the web UI: each kind's root and scope, the tree, and reading a file
(docs/specs/web-ui.md#file-api-rules)."""

import hashlib
from pathlib import Path

import pytest

from coding_study.application.attempt_files import (
    EDITABLE_BYTES,
    StartedFile,
    attempt_tree,
    read_attempt_file,
)
from coding_study.application.attempt_status import attempt_status
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import UnknownFileError, UsageError
from coding_study.domain.file_states import FileState
from coding_study.domain.problem import Language
from coding_study.domain.project_manifest import FileOrigin
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

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
