"""A workspace's languages, added and removed (docs/specs/cli.md#cstudy-lang): the marker, the
template files of an added language, and what a removal leaves in place."""

from pathlib import Path

import pytest

from coding_study.adapters.workspace_marker import read_marker
from coding_study.adapters.workspace_setup import FsWorkspaceLanguageStore, FsWorkspaceSetup
from coding_study.application.workspace_languages import (
    FolderState,
    LanguageRequest,
    change_languages,
    removal_plan,
    workspace_languages,
)
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import ALL_LANGUAGES, Language
from tests.fakes import NOW, make_environment
from tests.helpers import SCHEMAS_DIRECTORY

PYTHON, TYPESCRIPT, JAVA, KOTLIN, GO, RUST = ALL_LANGUAGES
PRACTICE_FILE = "rust/practice/lru_cache.rs"
SHARED = ("README.md", ".gitignore", "notes/.gitkeep")


def workspace(tmp_path: Path, languages: tuple[Language, ...] | None = None):
    """A workspace made as `cstudy init` makes it, with `languages` in its marker, and the
    environment over it."""
    root = tmp_path / "ws"
    FsWorkspaceSetup(tmp_path / "runners", "0.1.0").write_missing(root, languages)
    (root / "schemas").symlink_to(SCHEMAS_DIRECTORY)
    environment = make_environment(root, workspace_languages=read_marker(root).languages)
    return environment, FsWorkspaceLanguageStore(root)


def marker_languages(environment) -> tuple[Language, ...] | None:
    return read_marker(environment.root).languages


def start_attempt(environment, language: Language, slug: str = "lru-cache"):
    return environment.progress.add_attempt(NewAttempt(slug, language, AttemptMode.NEW, NOW))


def test_a_workspace_that_chose_none_has_all_six(tmp_path):
    environment, _ = workspace(tmp_path)
    assert workspace_languages(environment) == ALL_LANGUAGES


def test_a_workspace_has_the_languages_of_its_marker(tmp_path):
    environment, _ = workspace(tmp_path, (PYTHON, GO))
    assert workspace_languages(environment) == (PYTHON, GO)


def test_adding_lists_the_language_in_workspace_order(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, RUST))
    change = change_languages(environment, store, LanguageRequest(add=(GO,)))
    assert (change.languages, marker_languages(environment)) == ((PYTHON, GO, RUST),) * 2


def test_adding_writes_the_languages_template_files_only(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    change = change_languages(environment, store, LanguageRequest(add=(GO,)))
    assert change.files is not None
    assert sorted(change.files.written) == ["go.work", "go/go.mod", "go/practice/.gitkeep"]


def test_adding_reports_no_shared_file_as_kept(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    change = change_languages(environment, store, LanguageRequest(add=(GO,)))
    assert change.files is not None
    assert change.files.kept == ()


def test_adding_never_overwrites_a_file_that_is_there(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    (environment.root / "go").mkdir()
    (environment.root / "go" / "go.mod").write_text("module mine\n")
    change = change_languages(environment, store, LanguageRequest(add=(GO,)))
    assert change.files is not None
    assert (change.files.kept, (environment.root / "go" / "go.mod").read_text()) == (
        ("go/go.mod",),
        "module mine\n",
    )


def test_adding_java_writes_the_shared_jvm_folder(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    change_languages(environment, store, LanguageRequest(add=(JAVA,)))
    assert (environment.root / "jvm" / "settings.gradle.kts").is_file()


def test_adding_kotlin_beside_java_keeps_the_jvm_folder(tmp_path):
    environment, store = workspace(tmp_path, (JAVA,))
    change = change_languages(environment, store, LanguageRequest(add=(KOTLIN,)))
    assert change.files is not None
    assert (change.files.written, len(change.files.kept) > 0) == ((), True)


def test_adding_leaves_the_shared_files_as_they_were(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    for relative in SHARED:
        (environment.root / relative).unlink()
    change_languages(environment, store, LanguageRequest(add=(GO,)))
    assert [(environment.root / relative).exists() for relative in SHARED] == [False] * 3


def test_a_language_already_there_changes_nothing(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    before = (environment.root / ".cs" / "workspace.toml").read_bytes()
    change = change_languages(environment, store, LanguageRequest(add=(GO,)))
    assert (
        change.added,
        change.already,
        change.files,
        (environment.root / ".cs" / "workspace.toml").read_bytes(),
    ) == ((), (GO,), None, before)


def test_adding_to_a_workspace_that_chose_none_changes_nothing(tmp_path):
    environment, store = workspace(tmp_path)
    before = (environment.root / ".cs" / "workspace.toml").read_bytes()
    change = change_languages(environment, store, LanguageRequest(add=(GO,)))
    assert (change.already, (environment.root / ".cs" / "workspace.toml").read_bytes()) == (
        (GO,),
        before,
    )


def test_adding_keeps_the_markers_comments_and_other_keys(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    marker = environment.root / ".cs" / "workspace.toml"
    marker.write_text(marker.read_text() + '\n[licenses.kotlin-lsp]\nname = "x"\nurl = "y"\n')
    change_languages(environment, store, LanguageRequest(add=(GO,)))
    text = marker.read_text()
    assert ("# coding-study workspace" in text, "[licenses.kotlin-lsp]" in text) == (True, True)
    assert marker_languages(environment) == (PYTHON, GO)


def test_removing_takes_the_language_out_of_the_marker(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    change_languages(environment, store, LanguageRequest(remove=(GO,)))
    assert marker_languages(environment) == (PYTHON,)


def test_removing_from_a_workspace_that_chose_none_writes_the_other_five(tmp_path):
    environment, store = workspace(tmp_path)
    change_languages(environment, store, LanguageRequest(remove=(RUST,)))
    assert marker_languages(environment) == (PYTHON, TYPESCRIPT, JAVA, KOTLIN, GO)


def test_removing_keeps_the_folder_and_its_practice_files(tmp_path):
    environment, store = workspace(tmp_path)
    (environment.root / PRACTICE_FILE).write_text("mine")
    change_languages(environment, store, LanguageRequest(remove=(RUST,)))
    assert (environment.root / PRACTICE_FILE).read_text() == "mine"


def test_removing_keeps_progress(tmp_path):
    environment, store = workspace(tmp_path)
    start_attempt(environment, RUST)
    change_languages(environment, store, LanguageRequest(remove=(RUST,)))
    assert len(environment.progress.attempts_in_progress()) == 1


def test_removing_says_the_folder_it_kept(tmp_path):
    environment, store = workspace(tmp_path)
    change = change_languages(environment, store, LanguageRequest(remove=(GO,)))
    assert change.removal is not None
    (folder,) = change.removal.folders
    assert (folder.paths, folder.state) == (("go", "go.work"), FolderState.PRESENT)


def test_a_folder_that_is_not_there_is_absent(tmp_path):
    environment, _ = workspace(tmp_path, (PYTHON, GO))
    plan = removal_plan(environment, (RUST,))
    assert [folder.state for folder in plan.folders] == [FolderState.ABSENT]


def test_removing_java_beside_kotlin_leaves_the_jvm_folder_in_use(tmp_path):
    environment, store = workspace(tmp_path, (JAVA, KOTLIN))
    change = change_languages(environment, store, LanguageRequest(remove=(JAVA,)))
    assert change.removal is not None
    (folder,) = change.removal.folders
    assert (folder.state, folder.users) == (FolderState.IN_USE, (KOTLIN,))


def test_removing_both_jvm_languages_makes_one_folder_of_it(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, JAVA, KOTLIN))
    change = change_languages(environment, store, LanguageRequest(remove=(JAVA, KOTLIN)))
    assert change.removal is not None
    assert [(folder.paths, folder.removed) for folder in change.removal.folders] == [
        (("jvm",), (JAVA, KOTLIN))
    ]


def test_removing_a_language_the_workspace_lacks_changes_nothing(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    before = (environment.root / ".cs" / "workspace.toml").read_bytes()
    change = change_languages(environment, store, LanguageRequest(remove=(RUST,)))
    assert change.removal is not None
    assert (
        change.removal.listed,
        change.removal.not_listed,
        (environment.root / ".cs" / "workspace.toml").read_bytes(),
    ) == ((), (RUST,), before)


def test_removing_the_last_language_is_refused(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    with pytest.raises(UsageError, match="a workspace needs at least one language"):
        change_languages(environment, store, LanguageRequest(remove=(PYTHON,)))


def test_removing_every_language_of_a_workspace_that_chose_none_is_refused(tmp_path):
    environment, store = workspace(tmp_path)
    with pytest.raises(UsageError, match="at least one language"):
        change_languages(environment, store, LanguageRequest(remove=ALL_LANGUAGES))


def test_a_refused_removal_changes_nothing(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    before = (environment.root / ".cs" / "workspace.toml").read_bytes()
    with pytest.raises(UsageError):
        change_languages(environment, store, LanguageRequest(remove=(PYTHON,)))
    assert (environment.root / ".cs" / "workspace.toml").read_bytes() == before


def test_removing_the_only_language_while_adding_another_is_allowed(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    change_languages(environment, store, LanguageRequest(add=(GO,), remove=(PYTHON,)))
    assert marker_languages(environment) == (GO,)


def test_adding_and_removing_the_same_language_is_refused(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    with pytest.raises(UsageError, match="cannot add and remove go in one change"):
        change_languages(environment, store, LanguageRequest(add=(GO,), remove=(GO,)))


def test_an_attempt_in_progress_in_a_removed_language_is_named(tmp_path):
    environment, store = workspace(tmp_path)
    attempt = start_attempt(environment, RUST)
    change = change_languages(environment, store, LanguageRequest(remove=(RUST,)))
    assert change.removal is not None
    assert change.removal.attempts == (attempt,)


def test_an_attempt_in_another_language_is_not(tmp_path):
    environment, store = workspace(tmp_path)
    start_attempt(environment, PYTHON)
    change = change_languages(environment, store, LanguageRequest(remove=(RUST,)))
    assert change.removal is not None
    assert change.removal.attempts == ()
