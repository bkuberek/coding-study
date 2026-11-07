"""`cstudy reset` (docs/specs/cli.md#cstudy-reset): what goes, what stays and what refuses."""

import shutil
from pathlib import Path
from typing import Any

import pytest

from coding_study.application.reset_workspace import ResetRequest, reset_preview, reset_workspace
from coding_study.domain.errors import ResetNotConfirmedError, UsageError, WorkspaceBusyError
from coding_study.domain.reset import RESET_WORD, ResetPreview
from tests.fakes import make_environment
from tests.helpers import SCHEMAS_DIRECTORY
from tests.stats_fixture import fill_progress

CARGO = """\
[package]
name = "practice"

[lib]
path = "lib.rs"

[[example]]
name = "two_sum"
path = "practice/two_sum.rs"
crate-type = ["lib"]
"""
KEPT_FILES = (
    "config.toml",
    ".cs/workspace.toml",
    ".cs/ide.json",
    ".cs/serve/preferences.json",
    ".cs/runtime/stamp.json",
    ".cs/lsp/package.json",
    ".cs/cases/two-sum.json",
    ".cs/calibration/python/two-sum.json",
    ".cs/build/python/ref.py",
    "python/pyproject.toml",
    "python/practice/.gitkeep",
    "problems/.gitkeep",
    "problems/0900-mine/meta.yaml",
    "progress-export.json",
    "go.work",
)
RUN_FOLDERS = (".cs/runs/20261106-1/out.json", ".cs/runs/20261106-2/out.json")
STATEMENTS = (".statements/two-sum.md",)
PRACTICE_FILES = (
    "python/practice/two_sum.py",
    "typescript/practice/two-sum.ts",
    "jvm/java/src/main/java/practice/two_sum/Solution.java",
    "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt",
    "go/practice/two_sum/two_sum.go",
    "rust/practice/two_sum.rs",
)
PROJECTS = ("projects/bank/bank/bank.py", "projects/bank/README.md", ".cs/projects/bank.json")
NOTES = ("notes/system-design/url-shortener.md",)
ARCHIVE = (".archive/two-sum/1-python/two_sum.py", ".archive/two-sum/2-python/two_sum.py")


def touch(root: Path, *paths: str) -> None:
    for path in paths:
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("x")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    touch(
        root,
        *KEPT_FILES,
        *RUN_FOLDERS,
        *STATEMENTS,
        *PRACTICE_FILES,
        *PROJECTS,
        *NOTES,
        *ARCHIVE,
        "notes/.gitkeep",
        "projects/.gitkeep",
    )
    (root / "rust/Cargo.toml").write_text(CARGO)
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas")
    return root


@pytest.fixture
def environment(root: Path):
    environment = make_environment(root)
    fill_progress(environment)
    return environment


class Quiet:
    def active_run(self) -> str | None:
        return None


class Busy:
    def active_run(self) -> str | None:
        return "a run is in progress: pid 123"


def existing(root: Path, *paths: str) -> list[str]:
    return [path for path in paths if (root / path).exists()]


def counts(preview, option: str | None) -> dict[str, int]:
    group = next(group for group in preview.groups if group.option == option)
    return {entry.label: entry.count for entry in group.entries}


def reset(environment, **options: Any) -> ResetPreview:
    request = ResetRequest(word=RESET_WORD, **options)
    return reset_workspace(environment, request, Quiet())


# The preview


def test_the_preview_counts_the_progress_by_table(environment):
    found = counts(reset_preview(environment, Quiet()), None)
    assert (found["attempts"], found["test runs"], found["scheduled reviews"]) == (6, 4, 3)


def test_the_preview_counts_the_bench_runs(environment):
    assert counts(reset_preview(environment, Quiet()), None)["bench runs"] == 3


def test_the_preview_counts_the_run_folders_and_statements(environment):
    found = counts(reset_preview(environment, Quiet()), None)
    assert (found["run folders"], found["rendered statements"]) == (2, 1)


def test_the_preview_counts_the_practice_files_project_folders_and_notes(environment):
    assert counts(reset_preview(environment, Quiet()), "files") == {
        "practice files": 6,
        "project folders": 1,
        "notes": 1,
    }


def test_the_preview_counts_the_archived_attempts(environment):
    assert counts(reset_preview(environment, Quiet()), "archive") == {"archived attempts": 2}


def test_the_preview_says_what_stays(environment):
    kept = " ".join(reset_preview(environment, Quiet()).kept)
    assert all(name in kept for name in ("config.toml", "preferences.json", "workspace.toml"))


def test_the_preview_deletes_nothing(environment, root):
    reset_preview(environment, Quiet())
    assert (
        environment.progress.snapshot().row_counts()["attempts"],
        existing(root, *RUN_FOLDERS),
    ) == (6, list(RUN_FOLDERS))


def test_the_preview_says_when_a_run_is_active(environment):
    assert reset_preview(environment, Busy()).busy == "a run is in progress: pid 123"


def test_a_workspace_without_progress_previews_zeros(root):
    assert counts(reset_preview(make_environment(root), Quiet()), None)["attempts"] == 0


# Progress is the default


def test_a_reset_empties_every_table_of_progress(environment):
    reset(environment)
    assert set(environment.progress.snapshot().row_counts().values()) == {0}


def test_a_reset_deletes_an_open_attempt(environment):
    assert environment.progress.attempts_in_progress() != ()
    reset(environment)
    assert environment.progress.attempts_in_progress() == ()


def test_a_reset_deletes_the_run_folders_and_statements(environment, root):
    reset(environment)
    assert existing(root, *RUN_FOLDERS, *STATEMENTS) == []


def test_a_reset_keeps_settings_toolchains_and_the_marker(environment, root):
    reset(environment)
    assert existing(root, *KEPT_FILES) == list(KEPT_FILES)


def test_a_reset_keeps_practice_files_project_folders_notes_and_the_archive_by_default(
    environment, root
):
    reset(environment)
    kept = (*PRACTICE_FILES, *PROJECTS, *NOTES, *ARCHIVE)
    assert existing(root, *kept) == list(kept)


def test_a_reset_answers_what_it_deleted(environment):
    assert reset(environment).groups[0].entries[0].count == 6


def test_a_reset_twice_finds_nothing_left(environment):
    reset(environment)
    assert counts(reset_preview(environment, Quiet()), None)["attempts"] == 0


# The options


def test_files_deletes_practice_files_project_folders_and_notes(environment, root):
    reset(environment, files=True)
    assert existing(root, *PRACTICE_FILES, *PROJECTS, *NOTES) == []


def test_files_keeps_what_the_template_put_in_those_folders(environment, root):
    reset(environment, files=True)
    kept = ("python/practice/.gitkeep", "notes/.gitkeep", "projects/.gitkeep")
    assert existing(root, *kept) == list(kept)


def test_files_keeps_the_archive(environment, root):
    reset(environment, files=True)
    assert existing(root, *ARCHIVE) == list(ARCHIVE)


def test_files_takes_the_started_problems_out_of_the_rust_manifest(environment, root):
    reset(environment, files=True)
    assert "[[example]]" not in (root / "rust/Cargo.toml").read_text()


def test_no_option_leaves_the_rust_manifest(environment, root):
    reset(environment)
    assert "[[example]]" in (root / "rust/Cargo.toml").read_text()


def test_archive_deletes_the_archive(environment, root):
    reset(environment, archive=True)
    assert existing(root, *ARCHIVE) == []


def test_archive_keeps_the_practice_files(environment, root):
    reset(environment, archive=True)
    assert existing(root, *PRACTICE_FILES) == list(PRACTICE_FILES)


# Refusals


@pytest.mark.parametrize("word", ["", "RESET", "reset ", "yes", None])
def test_any_other_word_is_refused_and_deletes_nothing(environment, root, word):
    with pytest.raises(ResetNotConfirmedError, match="can't be undone"):
        reset_workspace(environment, ResetRequest(word=word), Quiet())
    assert (
        environment.progress.snapshot().row_counts()["attempts"],
        existing(root, *RUN_FOLDERS),
    ) == (6, list(RUN_FOLDERS))


def test_an_active_run_is_refused_and_deletes_nothing(environment, root):
    with pytest.raises(WorkspaceBusyError, match="a run is in progress"):
        reset_workspace(environment, ResetRequest(word=RESET_WORD), Busy())
    assert (
        environment.progress.snapshot().row_counts()["attempts"],
        existing(root, *RUN_FOLDERS),
    ) == (6, list(RUN_FOLDERS))


def test_a_target_that_links_out_of_the_workspace_refuses_everything(environment, root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "projects/linked").symlink_to(outside)
    with pytest.raises(UsageError, match="projects/linked leaves the workspace"):
        reset_workspace(environment, ResetRequest(word=RESET_WORD, files=True), Quiet())
    assert (environment.progress.snapshot().row_counts()["attempts"], outside.exists()) == (6, True)


def test_a_link_inside_a_target_that_leaves_the_workspace_refuses_everything(
    environment, root, tmp_path
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "projects/bank/data").symlink_to(outside)
    with pytest.raises(UsageError, match="projects/bank/data leaves the workspace"):
        reset_workspace(environment, ResetRequest(word=RESET_WORD, files=True), Quiet())
    assert existing(root, *PROJECTS) == list(PROJECTS)


def test_a_folder_that_is_itself_a_link_out_of_the_workspace_refuses(environment, root, tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "keep.md").write_text("mine")
    for name in (".statements",):
        for found in (root / name).iterdir():
            found.unlink()
        (root / name).rmdir()
        (root / name).symlink_to(outside)
    with pytest.raises(UsageError, match=r"\.statements/keep\.md leaves the workspace"):
        reset_workspace(environment, ResetRequest(word=RESET_WORD), Quiet())
    assert (outside / "keep.md").read_text() == "mine"


def test_a_link_that_stays_in_the_workspace_is_removed_and_its_target_kept(environment, root):
    (root / "projects/bank/.venv").symlink_to(root / "python")
    reset(environment, files=True)
    assert (not (root / "projects/bank").exists(), (root / "python/pyproject.toml").exists()) == (
        True,
        True,
    )


SETS_FILE = "sets:\n  backend-loop:  # mine\n    problems:\n      - two-sum\n"


def test_the_preview_says_sets_are_kept(environment):
    kept = " ".join(reset_preview(environment, Quiet()).kept)
    assert "sets.yaml" in kept


@pytest.mark.parametrize(
    "options",
    [{}, {"files": True}, {"archive": True}, {"files": True, "archive": True}],
    ids=["plain", "files", "archive", "files and archive"],
)
def test_a_reset_keeps_sets_whatever_its_options(environment, root, options):
    (root / "sets.yaml").write_text(SETS_FILE)
    reset_workspace(environment, ResetRequest(RESET_WORD, **options), Quiet())
    assert (root / "sets.yaml").read_text() == SETS_FILE
