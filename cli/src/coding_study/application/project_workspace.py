"""A project problem's folder in the workspace: what `cstudy start` copies, links and archives
(docs/specs/cli.md#cstudy-start, installation-and-workspaces.md#project-folders).

A new attempt copies the starter into `projects/<slug>/` without overwriting a file; a resumed
attempt copies it only when the folder is missing, so a file you deleted or changed stays as it
is. Both link the folder to the workspace's toolchain when the link is missing or dangles: a
Python folder's `.venv` link, or the file through which a folder reaches it, written when it is
missing: a Go folder's own `go.work`, a Rust folder's `.cargo/config.toml`.
`--fresh` and review attempts first archive the folder, without what tools wrote into it.
"""

from dataclasses import dataclass

from coding_study.application.active_attempt import autograded_language
from coding_study.application.ports import Workspace
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import ContentError, ContentIssue, UsageError
from coding_study.domain.problem import Problem
from coding_study.domain.problem_files import STARTER_DIRECTORY
from coding_study.domain.project import ProjectTree
from coding_study.domain.workspace_projects import (
    folder_language,
    project_folder,
    toolchain_files,
    toolchain_link,
)

NOT_TEXT = "is not UTF-8 text: a starter holds text files only"
NO_STARTER = "is missing: cstudy start copies it into the workspace"


@dataclass(frozen=True, slots=True)
class SeededProject:
    folder: str
    """`projects/<slug>`, relative to the workspace root."""
    copied: tuple[str, ...]
    """The starter files this call wrote, relative to the folder, in path order."""
    linked: bool
    """This call created or recreated the folder's link to the toolchain, or wrote a toolchain
    file it lacked."""


def seed_project(workspace: Workspace, problem: Problem) -> SeededProject:
    """A new attempt's folder: every starter file it lacks, never overwriting one, and the link.

    Raises ContentError, before writing anything, for a missing starter or one holding a file
    that is not text.
    """
    folder = project_folder(problem.meta.slug)
    copied = _copy_starter(workspace, problem, folder)
    linked = _link(workspace, problem, folder)
    return SeededProject(folder, copied, linked)


def resume_project(workspace: Workspace, problem: Problem) -> SeededProject:
    """A resumed attempt's folder: the starter only when the folder is missing, and the link.

    Raises ContentError as `seed_project` does.
    """
    folder = project_folder(problem.meta.slug)
    copied = () if workspace.exists(folder) else _copy_starter(workspace, problem, folder)
    linked = _link(workspace, problem, folder)
    return SeededProject(folder, copied, linked)


def archive_project(workspace: Workspace, owner: Attempt) -> str | None:
    """Moves the folder into the archive directory of `owner`, the attempt that wrote it, and
    returns that directory; None when there is no folder.

    Raises UsageError, before moving anything, when that directory exists: an archived attempt is
    never overwritten.
    """
    folder = project_folder(owner.slug)
    if not workspace.exists(folder):
        return None
    destination = layout.archive_directory(owner.slug, owner.id, autograded_language(owner))
    if workspace.exists(destination):
        raise UsageError(
            f"cannot archive {folder}: {destination} already exists; "
            f"move that directory aside, then start again"
        )
    workspace.archive_folder(folder, destination)
    return destination


def _copy_starter(workspace: Workspace, problem: Problem, folder: str) -> tuple[str, ...]:
    starter = _starter(problem)
    missing = [file for file in starter.files if not workspace.exists(f"{folder}/{file.path}")]
    unreadable = [file.path for file in missing if file.text is None]
    if unreadable:
        source = _starter_source(problem)
        raise ContentError([ContentIssue(f"{source}/{path}", "", NOT_TEXT) for path in unreadable])
    texts = {file.path: file.text for file in missing if file.text is not None}
    for path, text in texts.items():
        workspace.write_text(f"{folder}/{path}", text)
    return tuple(texts)


def _starter(problem: Problem) -> ProjectTree:
    if problem.project_files is None:
        raise ValueError(f"{problem.meta.slug} is not a project problem")
    starter = problem.project_files.starter
    if starter is None:
        raise ContentError([ContentIssue(_starter_source(problem), "", NO_STARTER)])
    return starter


def _starter_source(problem: Problem) -> str:
    return f"{problem.meta.directory_name}/{STARTER_DIRECTORY}"


def _link(workspace: Workspace, problem: Problem, folder: str) -> bool:
    language = folder_language(problem.meta)
    if language is None:
        return False
    missing = [
        file for file in toolchain_files(language) if not workspace.exists(f"{folder}/{file.path}")
    ]
    for file in missing:
        workspace.write_text(f"{folder}/{file.path}", file.text)
    link = toolchain_link(language)
    linked = link is not None and workspace.ensure_link(f"{folder}/{link.path}", link.target)
    return linked or bool(missing)
