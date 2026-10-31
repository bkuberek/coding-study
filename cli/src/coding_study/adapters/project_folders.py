"""A folder's files as `cstudy test --watch`, `code_hash` and archives see them: the tracked ones,
without the `.venv` link, `node_modules`, caches and `uv.lock` that tools write
(docs/specs/installation-and-workspaces.md#project-folders); and the Go folders of a workspace as
`cstudy doctor` checks them.

A link to a directory is never followed, so no walk leaves the folder through the `.venv` link,
and removing that link never deletes the shared venv it points to.
"""

import shutil
from collections.abc import Iterator
from pathlib import Path

from coding_study.domain.problem import Language
from coding_study.domain.workspace_projects import (
    GO_MODULE_FILE,
    PROJECTS_DIRECTORY,
    GoProjectFolder,
    go_module_file,
    is_untracked,
    project_folder,
    toolchain_files,
)

_LOCAL_REPLACEMENT_PREFIXES = ("./", "../", "/")
"""A `replace` target that is a directory, not another module."""


def tracked_files(folder: Path) -> list[Path]:
    """Every tracked file under `folder`, in path order; none when it is not a directory."""
    if not folder.is_dir():
        return []
    return sorted(
        entry
        for entry in _entries(folder, folder)
        if entry.is_file() and not _untracked(folder, entry)
    )


def remove_untracked(folder: Path) -> None:
    """Deletes every untracked entry under `folder`; a link is removed, never followed."""
    untracked = [entry for entry in _entries(folder, folder) if _untracked(folder, entry)]
    for entry in untracked:
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def _entries(folder: Path, directory: Path) -> Iterator[Path]:
    """Every entry under `directory`, descending only into tracked directories that are not
    links."""
    for entry in directory.iterdir():
        yield entry
        if entry.is_dir() and not entry.is_symlink() and not _untracked(folder, entry):
            yield from _entries(folder, entry)


def _untracked(folder: Path, entry: Path) -> bool:
    return is_untracked(entry.relative_to(folder).as_posix())


def go_project_folders(root: Path) -> tuple[GoProjectFolder, ...]:
    """Every folder in the workspace `root`'s `projects/` that holds a `go.mod`, in name order."""
    projects = root / PROJECTS_DIRECTORY
    if not projects.is_dir():
        return ()
    folders = sorted(folder for folder in projects.iterdir() if (folder / GO_MODULE_FILE).is_file())
    return tuple(_go_folder(folder) for folder in folders)


def write_missing_go_work_files(root: Path) -> tuple[str, ...]:
    """Writes the `go.work` of each Go folder that lacks one; returns those folders."""
    written: list[str] = []
    for found in go_project_folders(root):
        if found.has_work_file:
            continue
        for file in toolchain_files(Language.GO):
            path = root / found.folder / file.path
            if not path.exists():
                path.write_text(file.text, encoding="utf-8")
        written.append(found.folder)
    return tuple(written)


def _go_folder(folder: Path) -> GoProjectFolder:
    module = go_module_file((folder / GO_MODULE_FILE).read_text(encoding="utf-8", errors="replace"))
    unresolved = tuple(
        target
        for target in module.replaces.values()
        if target.startswith(_LOCAL_REPLACEMENT_PREFIXES) and not (folder / target).is_dir()
    )
    work_files = (folder / file.path for file in toolchain_files(Language.GO))
    return GoProjectFolder(
        project_folder(folder.name),
        module.module,
        has_work_file=all(path.is_file() for path in work_files),
        unresolved=unresolved,
    )
