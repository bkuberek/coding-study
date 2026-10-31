"""Project folders in the workspace (docs/specs/installation-and-workspaces.md#project-folders).

`cstudy start` fills `projects/<slug>/` from a project problem's starter and links it to the
workspace's toolchain. What tools write into a folder is untracked, as the workspace's
`.gitignore` has it: the `.venv` link, `node_modules`, caches and a `uv.lock`. `cstudy test --watch`
ignores those, `code_hash` leaves them out, and an archived attempt goes without them. Paths are
POSIX strings, relative to the workspace root or, where a name says so, to the folder.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from coding_study.domain import layout
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta
from coding_study.domain.project import PATH_SEPARATOR

PROJECTS_DIRECTORY = "projects"
PYTEST_INSTALL_COMMAND = f"uv add --dev pytest --directory {layout.PYTHON_PROJECT}"
"""A Python project's tests run in the workspace venv; workspaces created before the template
listed pytest lack it."""
UNTRACKED_DIRECTORIES = frozenset(
    {layout.PYTHON_VENV, "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
)
"""Untracked wherever they appear in a folder."""
UNTRACKED_ROOT_FILES = frozenset({"uv.lock"})
"""Untracked at the root of a folder only: a plain `uv run` there writes one."""
_FOLDER_TO_WORKSPACE_ROOT = "../.."
"""From `projects/<slug>/` up to the workspace root."""


@dataclass(frozen=True, slots=True)
class ToolchainLink:
    """A symbolic link that reaches the workspace's toolchain from a project folder."""

    path: str
    """Relative to the folder."""
    target: str
    """Relative to the folder, so the link survives moving and cloning the workspace."""


def project_folder(slug: str) -> str:
    return f"{PROJECTS_DIRECTORY}{PATH_SEPARATOR}{slug}"


def folder_language(meta: ProblemMeta) -> Language | None:
    """The language of a project problem's folder, the one its problem lists (check S14); None
    for a problem of another kind, which has no folder."""
    return meta.languages[0] if meta.kind is ProblemKind.PROJECT else None


def toolchain_link(language: Language) -> ToolchainLink | None:
    """Python folders link `.venv` to the workspace venv; the others reach their toolchain through
    their build files and need no link."""
    if language is Language.PYTHON:
        venv = PATH_SEPARATOR.join(
            (_FOLDER_TO_WORKSPACE_ROOT, layout.PYTHON_PROJECT, layout.PYTHON_VENV)
        )
        return ToolchainLink(layout.PYTHON_VENV, venv)
    return None


def is_untracked(path: str) -> bool:
    """Whether `path`, relative to a project folder, is something a tool wrote."""
    return path in UNTRACKED_ROOT_FILES or _names_untracked(path.split(PATH_SEPARATOR))


def project_slug(path: str) -> str | None:
    """The folder, which is the problem's slug, that the file `path` lies in; None for a path
    outside every project folder or under one's `.venv`, `node_modules` or caches
    (docs/specs/cli.md#solution-file-targets)."""
    match path.split(PATH_SEPARATOR):
        case [directory, slug, *directories, _file] if directory == PROJECTS_DIRECTORY and slug:
            return None if _names_untracked(directories) else slug
        case _:
            return None


def _names_untracked(segments: Sequence[str]) -> bool:
    return any(segment in UNTRACKED_DIRECTORIES for segment in segments)
