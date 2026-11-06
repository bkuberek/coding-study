"""`cstudy reset` and the Settings view's Danger section (docs/specs/cli.md#cstudy-reset): deletes
progress and what is derived from it, and with options the user's files. Nothing is deleted until
the word is given, no run is active and every target is known to stay inside the workspace.

The database goes first, in one transaction: a reset interrupted after it leaves files that the
next reset finds and deletes, and a database that is whole.
"""

from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.ports import RunActivity, Workspace
from coding_study.domain.errors import ResetNotConfirmedError, UsageError, WorkspaceBusyError
from coding_study.domain.layout import (
    ARCHIVE_DIRECTORY,
    NOTES_DIRECTORY,
    RUNS_DIRECTORY,
    STATEMENTS_DIRECTORY,
    user_directory,
)
from coding_study.domain.practice_manifests import RUST_MANIFEST, without_problems
from coding_study.domain.problem import Language
from coding_study.domain.project import PATH_SEPARATOR, relative_path_issue
from coding_study.domain.project_manifest import MANIFESTS_DIRECTORY
from coding_study.domain.reset import (
    KEPT,
    RESET_WARNING,
    RESET_WORD,
    ResetEntry,
    ResetGroup,
    ResetOption,
    ResetPreview,
)
from coding_study.domain.workspace_projects import PROJECTS_DIRECTORY

KEEP_FILE = ".gitkeep"
"""What the workspace template puts in a folder of the user's, so the folder stays in git."""
TABLE_LABELS = (
    ("attempts", "attempts"),
    ("test_runs", "test runs"),
    ("schedule", "scheduled reviews"),
    ("bench_runs", "bench runs"),
    ("submissions", "submissions"),
    ("level_unlocks", "level unlocks"),
)


@dataclass(frozen=True, slots=True)
class ResetRequest:
    word: str | None
    """Must be `RESET_WORD`."""
    files: bool = False
    archive: bool = False


def reset_preview(environment: Environment, activity: RunActivity) -> ResetPreview:
    return ResetPreview(_groups(environment), KEPT, activity.active_run())


def reset_workspace(
    environment: Environment, request: ResetRequest, activity: RunActivity
) -> ResetPreview:
    """Answers what it deleted. Raises ResetNotConfirmedError without the word, WorkspaceBusyError
    while a run or a job is active and UsageError when a target leaves the workspace, each having
    deleted nothing."""
    if request.word != RESET_WORD:
        raise ResetNotConfirmedError(f"type {RESET_WORD} to confirm. {RESET_WARNING}")
    busy = activity.active_run()
    if busy is not None:
        raise WorkspaceBusyError(f"cstudy reset waits until it ends: {busy}")
    workspace = environment.workspace
    targets = _targets(workspace, request)
    _refuse_what_leaves(workspace, targets)
    preview = _selected(reset_preview(environment, activity), request)
    environment.progress.clear()
    for target in targets:
        workspace.remove_entry(target)
    if request.files:
        _forget_started_problems(workspace)
    return preview


def _selected(preview: ResetPreview, request: ResetRequest) -> ResetPreview:
    chosen = {ResetOption.FILES: request.files, ResetOption.ARCHIVE: request.archive}
    groups = (group for group in preview.groups if group.option is None or chosen[group.option])
    return replace(preview, groups=tuple(groups))


def _groups(environment: Environment) -> tuple[ResetGroup, ...]:
    workspace = environment.workspace
    rows = environment.progress.snapshot().row_counts()
    tables = (ResetEntry(label, rows.get(table, 0)) for table, label in TABLE_LABELS)
    return (
        ResetGroup(
            None,
            "progress and state",
            (
                *tables,
                ResetEntry("run folders", len(workspace.entries(RUNS_DIRECTORY))),
                ResetEntry("rendered statements", len(workspace.entries(STATEMENTS_DIRECTORY))),
            ),
        ),
        ResetGroup(
            ResetOption.FILES,
            "practice files, project folders and notes",
            (
                ResetEntry("practice files", _own_files(workspace, *_practice_directories())),
                ResetEntry("project folders", len(_own_entries(workspace, PROJECTS_DIRECTORY))),
                ResetEntry("notes", _own_files(workspace, NOTES_DIRECTORY)),
            ),
        ),
        ResetGroup(
            ResetOption.ARCHIVE,
            f"{ARCHIVE_DIRECTORY}/, the files of earlier attempts",
            (ResetEntry("archived attempts", _archived_attempts(workspace)),),
        ),
    )


def _practice_directories() -> tuple[str, ...]:
    return tuple(dict.fromkeys(user_directory(language) for language in Language))


def _own_entries(workspace: Workspace, directory: str) -> tuple[str, ...]:
    return tuple(
        f"{directory}{PATH_SEPARATOR}{name}"
        for name in workspace.entries(directory)
        if name != KEEP_FILE
    )


def _own_files(workspace: Workspace, *directories: str) -> int:
    return sum(
        path != KEEP_FILE
        for directory in directories
        for path in workspace.tracked_files(directory)
    )


def _archived_attempts(workspace: Workspace) -> int:
    return sum(
        len(workspace.entries(f"{ARCHIVE_DIRECTORY}{PATH_SEPARATOR}{slug}"))
        for slug in workspace.entries(ARCHIVE_DIRECTORY)
    )


def _targets(workspace: Workspace, request: ResetRequest) -> tuple[str, ...]:
    directories = [RUNS_DIRECTORY, STATEMENTS_DIRECTORY]
    if request.files:
        directories += [
            *_practice_directories(),
            PROJECTS_DIRECTORY,
            MANIFESTS_DIRECTORY,
            NOTES_DIRECTORY,
        ]
    if request.archive:
        directories.append(ARCHIVE_DIRECTORY)
    return tuple(
        target for directory in directories for target in _own_entries(workspace, directory)
    )


def _refuse_what_leaves(workspace: Workspace, targets: tuple[str, ...]) -> None:
    for target in targets:
        issue = relative_path_issue(target)
        if issue is not None:
            raise UsageError(f"cstudy reset refuses {target}: it {issue}")
        leaving = workspace.leaving_entry(target)
        if leaving is not None:
            raise UsageError(
                f"{leaving} leaves the workspace, so cstudy reset deleted nothing; "
                "remove the link first"
            )


def _forget_started_problems(workspace: Workspace) -> None:
    """`rust/Cargo.toml` lists each started problem's file, which is gone now."""
    if workspace.exists(RUST_MANIFEST):
        text = workspace.read_text(RUST_MANIFEST)
        workspace.write_text(RUST_MANIFEST, without_problems(text))
