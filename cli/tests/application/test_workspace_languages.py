"""A workspace's languages, added and removed (docs/specs/cli.md#cstudy-lang): the marker, the
template files of an added language, and what a removal leaves in place."""

from pathlib import Path

import pytest

from coding_study.adapters.language_folders import FsLanguageFolders
from coding_study.adapters.workspace_marker import read_marker
from coding_study.adapters.workspace_setup import FsWorkspaceLanguageStore, FsWorkspaceSetup
from coding_study.application.workspace_languages import (
    FolderState,
    LanguageRequest,
    change_languages,
    language_removal_preview,
    removal_plan,
    workspace_languages,
)
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.errors import FolderNotDeletedError, UsageError, WorkspaceBusyError
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
    environment.progress.attempts_in_progress()  # creates progress.db, as every command does
    return environment, FsWorkspaceLanguageStore(root)


class Activity:
    """What a run or a job is doing: nothing, unless `busy` says what."""

    def __init__(self, busy: str | None = None) -> None:
        self._busy = busy

    def active_run(self) -> str | None:
        return self._busy


def apply(environment, store, request, activity: Activity | None = None):
    folders = FsLanguageFolders(environment.root)
    return change_languages(environment, store, folders, activity or Activity(), request)


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
    change = apply(environment, store, LanguageRequest(add=(GO,)))
    assert (change.languages, marker_languages(environment)) == ((PYTHON, GO, RUST),) * 2


def test_adding_writes_the_languages_template_files_only(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    change = apply(environment, store, LanguageRequest(add=(GO,)))
    assert change.files is not None
    assert sorted(change.files.written) == ["go.work", "go/go.mod", "go/practice/.gitkeep"]


def test_adding_reports_no_shared_file_as_kept(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    change = apply(environment, store, LanguageRequest(add=(GO,)))
    assert change.files is not None
    assert change.files.kept == ()


def test_adding_never_overwrites_a_file_that_is_there(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    (environment.root / "go").mkdir()
    (environment.root / "go" / "go.mod").write_text("module mine\n")
    change = apply(environment, store, LanguageRequest(add=(GO,)))
    assert change.files is not None
    assert (change.files.kept, (environment.root / "go" / "go.mod").read_text()) == (
        ("go/go.mod",),
        "module mine\n",
    )


def test_adding_java_writes_the_shared_jvm_folder(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    apply(environment, store, LanguageRequest(add=(JAVA,)))
    assert (environment.root / "jvm" / "settings.gradle.kts").is_file()


def test_adding_kotlin_beside_java_keeps_the_jvm_folder(tmp_path):
    environment, store = workspace(tmp_path, (JAVA,))
    change = apply(environment, store, LanguageRequest(add=(KOTLIN,)))
    assert change.files is not None
    assert (change.files.written, len(change.files.kept) > 0) == ((), True)


def test_adding_leaves_the_shared_files_as_they_were(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    for relative in SHARED:
        (environment.root / relative).unlink()
    apply(environment, store, LanguageRequest(add=(GO,)))
    assert [(environment.root / relative).exists() for relative in SHARED] == [False] * 3


def test_a_language_already_there_changes_nothing(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    before = (environment.root / ".cs" / "workspace.toml").read_bytes()
    change = apply(environment, store, LanguageRequest(add=(GO,)))
    assert (
        change.added,
        change.already,
        change.files,
        (environment.root / ".cs" / "workspace.toml").read_bytes(),
    ) == ((), (GO,), None, before)


def test_adding_to_a_workspace_that_chose_none_changes_nothing(tmp_path):
    environment, store = workspace(tmp_path)
    before = (environment.root / ".cs" / "workspace.toml").read_bytes()
    change = apply(environment, store, LanguageRequest(add=(GO,)))
    assert (change.already, (environment.root / ".cs" / "workspace.toml").read_bytes()) == (
        (GO,),
        before,
    )


def test_adding_keeps_the_markers_comments_and_other_keys(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    marker = environment.root / ".cs" / "workspace.toml"
    marker.write_text(marker.read_text() + '\n[licenses.kotlin-lsp]\nname = "x"\nurl = "y"\n')
    apply(environment, store, LanguageRequest(add=(GO,)))
    text = marker.read_text()
    assert ("# coding-study workspace" in text, "[licenses.kotlin-lsp]" in text) == (True, True)
    assert marker_languages(environment) == (PYTHON, GO)


def test_removing_takes_the_language_out_of_the_marker(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    apply(environment, store, LanguageRequest(remove=(GO,)))
    assert marker_languages(environment) == (PYTHON,)


def test_removing_from_a_workspace_that_chose_none_writes_the_other_five(tmp_path):
    environment, store = workspace(tmp_path)
    apply(environment, store, LanguageRequest(remove=(RUST,)))
    assert marker_languages(environment) == (PYTHON, TYPESCRIPT, JAVA, KOTLIN, GO)


def test_removing_keeps_the_folder_and_its_practice_files(tmp_path):
    environment, store = workspace(tmp_path)
    (environment.root / PRACTICE_FILE).write_text("mine")
    apply(environment, store, LanguageRequest(remove=(RUST,)))
    assert (environment.root / PRACTICE_FILE).read_text() == "mine"


def test_removing_keeps_progress(tmp_path):
    environment, store = workspace(tmp_path)
    start_attempt(environment, RUST)
    apply(environment, store, LanguageRequest(remove=(RUST,)))
    assert len(environment.progress.attempts_in_progress()) == 1


def test_removing_says_the_folder_it_kept(tmp_path):
    environment, store = workspace(tmp_path)
    change = apply(environment, store, LanguageRequest(remove=(GO,)))
    assert change.removal is not None
    (folder,) = change.removal.folders
    assert (folder.paths, folder.state) == (("go", "go.work"), FolderState.PRESENT)


def test_a_folder_that_is_not_there_is_absent(tmp_path):
    environment, _ = workspace(tmp_path, (PYTHON, GO))
    plan = removal_plan(environment, FsLanguageFolders(environment.root), (RUST,))
    assert [folder.state for folder in plan.folders] == [FolderState.ABSENT]


def test_removing_java_beside_kotlin_leaves_the_jvm_folder_in_use(tmp_path):
    environment, store = workspace(tmp_path, (JAVA, KOTLIN))
    change = apply(environment, store, LanguageRequest(remove=(JAVA,)))
    assert change.removal is not None
    (folder,) = change.removal.folders
    assert (folder.state, folder.users) == (FolderState.IN_USE, (KOTLIN,))


def test_removing_both_jvm_languages_makes_one_folder_of_it(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, JAVA, KOTLIN))
    change = apply(environment, store, LanguageRequest(remove=(JAVA, KOTLIN)))
    assert change.removal is not None
    assert [(folder.paths, folder.removed) for folder in change.removal.folders] == [
        (("jvm",), (JAVA, KOTLIN))
    ]


def test_removing_a_language_the_workspace_lacks_changes_nothing(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    before = (environment.root / ".cs" / "workspace.toml").read_bytes()
    change = apply(environment, store, LanguageRequest(remove=(RUST,)))
    assert change.removal is not None
    assert (
        change.removal.listed,
        change.removal.not_listed,
        (environment.root / ".cs" / "workspace.toml").read_bytes(),
    ) == ((), (RUST,), before)


def test_removing_the_last_language_is_refused(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    with pytest.raises(UsageError, match="a workspace needs at least one language"):
        apply(environment, store, LanguageRequest(remove=(PYTHON,)))


def test_removing_every_language_of_a_workspace_that_chose_none_is_refused(tmp_path):
    environment, store = workspace(tmp_path)
    with pytest.raises(UsageError, match="at least one language"):
        apply(environment, store, LanguageRequest(remove=ALL_LANGUAGES))


def test_a_refused_removal_changes_nothing(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    before = (environment.root / ".cs" / "workspace.toml").read_bytes()
    with pytest.raises(UsageError):
        apply(environment, store, LanguageRequest(remove=(PYTHON,)))
    assert (environment.root / ".cs" / "workspace.toml").read_bytes() == before


def test_removing_the_only_language_while_adding_another_is_allowed(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    apply(environment, store, LanguageRequest(add=(GO,), remove=(PYTHON,)))
    assert marker_languages(environment) == (GO,)


def test_adding_and_removing_the_same_language_is_refused(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    with pytest.raises(UsageError, match="cannot add and remove go in one change"):
        apply(environment, store, LanguageRequest(add=(GO,), remove=(GO,)))


def test_an_attempt_in_progress_in_a_removed_language_is_named(tmp_path):
    environment, store = workspace(tmp_path)
    attempt = start_attempt(environment, RUST)
    change = apply(environment, store, LanguageRequest(remove=(RUST,)))
    assert change.removal is not None
    assert change.removal.attempts == (attempt,)


def test_an_attempt_in_another_language_is_not(tmp_path):
    environment, store = workspace(tmp_path)
    start_attempt(environment, PYTHON)
    change = apply(environment, store, LanguageRequest(remove=(RUST,)))
    assert change.removal is not None
    assert change.removal.attempts == ()


# `--delete-folder`: docs/specs/cli.md#deleting-a-languages-folder

MARKER_FILE = ".cs/workspace.toml"
NO_MARKER = (PYTHON, TYPESCRIPT, JAVA, KOTLIN, GO)
"""What a workspace that chose none lists once Rust is removed."""


def delete(*languages: Language) -> LanguageRequest:
    return LanguageRequest(remove=languages, delete_folders=True)


def preview(environment, *languages: Language, activity: Activity | None = None):
    folders = FsLanguageFolders(environment.root)
    return language_removal_preview(environment, folders, activity or Activity(), languages)


def files_of(root: Path) -> dict[str, bytes]:
    """Every file under `root` by path, links not followed."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def outside_folder(files: dict[str, bytes], folder: str) -> dict[str, bytes]:
    """`files` but for those of `folder` and the marker, which a removal changes."""
    return {
        path: data
        for path, data in files.items()
        if not path.startswith(f"{folder}/") and path != MARKER_FILE
    }


def link_to(path: Path, target: Path) -> None:
    path.symlink_to(target, target_is_directory=target.is_dir())


def test_the_preview_counts_the_practice_files_of_the_folder(tmp_path):
    environment, _ = workspace(tmp_path)
    for name in ("lru_cache.rs", "two_sum.rs"):
        (environment.root / "rust" / "practice" / name).write_text("mine")
    (folder,) = preview(environment, RUST).folders
    assert (folder.state, folder.practice_files) == (FolderState.PRESENT, 2)


def test_the_gitkeep_is_no_practice_file(tmp_path):
    environment, _ = workspace(tmp_path)
    (folder,) = preview(environment, RUST).folders
    assert folder.practice_files == 0


def test_the_preview_counts_the_files_of_both_jvm_languages(tmp_path):
    environment, _ = workspace(tmp_path)
    for language in ("java", "kotlin"):
        practice = environment.root / "jvm" / language / "src" / "main" / language / "practice"
        practice.mkdir(parents=True, exist_ok=True)
        (practice / "Solution").write_text("mine")
    (folder,) = preview(environment, JAVA, KOTLIN).folders
    assert (folder.paths, folder.practice_files) == (("jvm",), 2)


def test_the_preview_changes_nothing(tmp_path):
    environment, _ = workspace(tmp_path)
    before = files_of(environment.root)
    preview(environment, RUST)
    assert files_of(environment.root) == before


def test_deleting_removes_the_folder_whole_with_its_toolchain_files(tmp_path):
    environment, store = workspace(tmp_path)
    (environment.root / "rust" / "target" / "debug").mkdir(parents=True)
    (environment.root / "rust" / "target" / "debug" / "deps").write_text("built")
    apply(environment, store, delete(RUST))
    assert not (environment.root / "rust").exists()


def test_deleting_says_what_it_deleted(tmp_path):
    environment, store = workspace(tmp_path)
    change = apply(environment, store, delete(RUST))
    assert [folder.paths for folder in change.deleted] == [("rust",)]


def test_deleting_go_deletes_go_work_too(tmp_path):
    environment, store = workspace(tmp_path)
    apply(environment, store, delete(GO))
    assert [(environment.root / name).exists() for name in ("go", "go.work")] == [False, False]


def test_deleting_one_jvm_language_keeps_the_folder_the_other_uses(tmp_path):
    environment, store = workspace(tmp_path)
    change = apply(environment, store, delete(JAVA))
    assert ((environment.root / "jvm").is_dir(), change.deleted) == (True, ())


def test_deleting_both_jvm_languages_deletes_the_folder(tmp_path):
    environment, store = workspace(tmp_path)
    apply(environment, store, delete(JAVA, KOTLIN))
    assert not (environment.root / "jvm").exists()


def test_deleting_java_while_kotlin_is_not_listed_deletes_the_folder(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, JAVA))
    apply(environment, store, delete(JAVA))
    assert not (environment.root / "jvm").exists()


def test_deleting_changes_the_marker_too(tmp_path):
    environment, store = workspace(tmp_path)
    apply(environment, store, delete(RUST))
    assert marker_languages(environment) == NO_MARKER


def test_deleting_never_touches_what_is_not_the_languages(tmp_path):
    environment, store = workspace(tmp_path)
    start_attempt(environment, PYTHON, "two-sum")
    for relative in (
        ".archive/two-sum/1-rust/two_sum.rs",
        "projects/bank/Cargo.toml",
        "notes/mine.md",
        "problems/my-problem/meta.yaml",
        "sets.yaml",
    ):
        (environment.root / relative).parent.mkdir(parents=True, exist_ok=True)
        (environment.root / relative).write_text(relative)
    rows = environment.progress.snapshot().row_counts()
    before = outside_folder(files_of(environment.root), "rust")
    apply(environment, store, delete(RUST))
    assert (
        outside_folder(files_of(environment.root), "rust"),
        environment.progress.snapshot().row_counts(),
    ) == (before, rows)


def test_deleting_removes_a_link_inside_the_folder_as_a_link(tmp_path):
    environment, store = workspace(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("outside")
    link_to(environment.root / "rust" / "link", elsewhere)
    apply(environment, store, delete(RUST))
    assert ((environment.root / "rust").exists(), (elsewhere / "keep.txt").read_text()) == (
        False,
        "outside",
    )


def test_a_link_inside_a_folder_that_points_outside_does_not_refuse(tmp_path):
    environment, store = workspace(tmp_path)
    link_to(environment.root / "rust" / "system", Path("/usr/bin"))
    apply(environment, store, delete(RUST))
    assert not (environment.root / "rust").exists()


def test_a_language_the_workspace_no_longer_lists_has_its_leftover_folder_deleted(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    (environment.root / "rust").mkdir()
    (environment.root / "rust" / "lib.rs").write_text("mine")
    change = apply(environment, store, delete(RUST))
    assert change.removal is not None
    assert (
        (environment.root / "rust").exists(),
        marker_languages(environment),
        change.removal.not_listed,
    ) == (False, (PYTHON, GO), (RUST,))


def test_a_folder_that_is_gone_is_absent_and_deletes_nothing(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON, GO))
    change = apply(environment, store, delete(RUST))
    assert change.removal is not None
    assert (change.deleted, [folder.state for folder in change.removal.folders]) == (
        (),
        [FolderState.ABSENT],
    )


def test_an_attempt_in_progress_refuses_the_deletion_naming_it(tmp_path):
    environment, store = workspace(tmp_path)
    attempt = start_attempt(environment, RUST)
    before = files_of(environment.root)
    with pytest.raises(UsageError) as caught:
        apply(environment, store, delete(RUST))
    assert (str(caught.value), files_of(environment.root)) == (
        f"cannot delete rust/: attempt {attempt.id} (lru-cache, rust) is in progress; "
        "finish it with cstudy done or end it with cstudy abort, or remove rust without "
        "--delete-folder",
        before,
    )


def test_each_attempt_in_progress_is_named_on_its_own_line(tmp_path):
    environment, store = workspace(tmp_path)
    start_attempt(environment, RUST)
    start_attempt(environment, GO, "two-sum")
    with pytest.raises(UsageError) as caught:
        apply(environment, store, delete(GO, RUST))
    assert sorted(line.partition(":")[0] for line in str(caught.value).splitlines()) == [
        "cannot delete go/ and go.work",
        "cannot delete rust/",
    ]


def test_an_attempt_in_progress_in_a_language_that_stays_does_not_refuse(tmp_path):
    environment, store = workspace(tmp_path)
    start_attempt(environment, PYTHON)
    apply(environment, store, delete(RUST))
    assert not (environment.root / "rust").exists()


def test_a_refused_deletion_leaves_the_marker_as_it_was(tmp_path):
    environment, store = workspace(tmp_path)
    start_attempt(environment, RUST)
    with pytest.raises(UsageError):
        apply(environment, store, delete(RUST))
    assert marker_languages(environment) is None


def test_a_run_or_a_job_refuses_the_deletion(tmp_path):
    environment, store = workspace(tmp_path)
    busy = Activity("a run or a job is in progress (process 4242)")
    before = files_of(environment.root)
    with pytest.raises(WorkspaceBusyError) as caught:
        apply(environment, store, delete(RUST), busy)
    assert (str(caught.value), files_of(environment.root)) == (
        "cstudy lang remove waits until it ends: a run or a job is in progress (process 4242)",
        before,
    )


def test_a_run_does_not_refuse_a_removal_that_keeps_the_folder(tmp_path):
    environment, store = workspace(tmp_path)
    apply(environment, store, LanguageRequest(remove=(RUST,)), Activity("a run is in progress"))
    assert (environment.root / "rust").is_dir()


def test_a_folder_that_is_a_link_is_refused_and_its_target_stays(tmp_path):
    environment, store = workspace(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("outside")
    (environment.root / "rust").rename(tmp_path / "moved-rust")
    link_to(environment.root / "rust", elsewhere)
    with pytest.raises(UsageError) as caught:
        apply(environment, store, delete(RUST))
    assert (
        str(caught.value),
        (elsewhere / "keep.txt").read_text(),
        marker_languages(environment),
    ) == (
        "rust leaves the workspace, so cstudy lang remove deleted nothing; remove the link first",
        "outside",
        None,
    )


def test_a_link_to_a_place_inside_the_workspace_is_still_a_link(tmp_path):
    environment, store = workspace(tmp_path)
    (environment.root / "go.work").unlink()
    link_to(environment.root / "go.work", environment.root / "README.md")
    with pytest.raises(UsageError, match=r"go\.work leaves the workspace"):
        apply(environment, store, delete(GO))


def test_every_folder_is_checked_before_any_is_deleted(tmp_path):
    environment, store = workspace(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (environment.root / "rust").rename(tmp_path / "moved-rust")
    link_to(environment.root / "rust", elsewhere)
    with pytest.raises(UsageError, match="rust leaves the workspace"):
        apply(environment, store, delete(GO, RUST))
    assert (environment.root / "go").is_dir()


def test_the_last_language_is_refused_before_any_other_check(tmp_path):
    environment, store = workspace(tmp_path, (PYTHON,))
    start_attempt(environment, PYTHON)
    with pytest.raises(UsageError, match="at least one language"):
        apply(environment, store, delete(PYTHON))


class Stubborn(FsLanguageFolders):
    """Folders that cannot be deleted whole."""

    def delete(self, path: str) -> None:
        raise FolderNotDeletedError(f"could not delete {path}/target: permission denied")


def test_a_folder_that_stays_in_part_is_raised_after_the_marker_changed(tmp_path):
    environment, store = workspace(tmp_path)
    folders = Stubborn(environment.root)
    with pytest.raises(FolderNotDeletedError, match="permission denied"):
        change_languages(environment, store, folders, Activity(), delete(RUST))
    assert marker_languages(environment) == NO_MARKER
