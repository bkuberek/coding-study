"""The Go row of `cstudy doctor`
(docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace): a Go project folder
needs its own `go.work`, a vendored `replace` that resolves and a module path of its own for the
go command and gopls."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from coding_study.adapters.project_folders import go_project_folders, write_missing_go_work_files
from coding_study.application.ports import FolderCheck
from coding_study.domain.layout import GO_WORK_FILE
from coding_study.domain.workspace_projects import (
    GO_MODULE_FILE,
    GoProjectFolder,
    go_folder_problems,
)

GO_PROJECTS_CHECK = "go projects"
MODULE_FIX = f"give each folder a module of its own in its {GO_MODULE_FILE}"
PROBLEM_SEPARATOR = "; "


@dataclass(frozen=True, slots=True)
class GoFolderChecks:
    """The folder checks of one workspace root."""

    root: Path

    def folder_checks(self) -> tuple[FolderCheck, ...]:
        return (go_folder_check(go_project_folders(self.root)),)

    def repair_folders(self) -> tuple[str, ...]:
        """Writes the `go.work` of every folder without one; a `go.work` of yours stays."""
        return tuple(
            f"{folder}/{GO_WORK_FILE}" for folder in write_missing_go_work_files(self.root)
        )


def go_folder_check(folders: Sequence[GoProjectFolder]) -> FolderCheck:
    """One sentence per problem, since a module that several folders declare is no one folder's
    problem."""
    problems = go_folder_problems(folders)
    counted = "problem" if len(problems) == 1 else "problems"
    fix = _fix(folders) if problems else None
    return FolderCheck(GO_PROJECTS_CHECK, problems, counted, fix, PROBLEM_SEPARATOR)


def _fix(folders: Sequence[GoProjectFolder]) -> str | None:
    """`--fix` writes a missing `go.work`; a `replace` that does not resolve comes back with the
    starter's `go.mod`; a shared module path needs an edit."""
    if any(not found.has_work_file for found in folders):
        return None
    unresolved = next((found for found in folders if found.unresolved), None)
    if unresolved is not None:
        slug = unresolved.folder.rpartition("/")[2]
        return f"cstudy start {slug} --restore {GO_MODULE_FILE}"
    return MODULE_FIX
