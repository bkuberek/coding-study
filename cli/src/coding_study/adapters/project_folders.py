"""A folder's files as `cstudy test --watch`, `code_hash` and archives see them: the tracked ones,
without the `.venv` link, `node_modules`, caches and `uv.lock` that tools write
(docs/specs/installation-and-workspaces.md#project-folders); the build folders `cstudy verify`
keeps in step with a problem's files (docs/specs/runners.md#reference-materialization); and the Go
folders of a workspace as `cstudy doctor` checks them.

A link to a directory is never followed, so no walk leaves the folder through the `.venv` link,
and removing that link never deletes the shared venv it points to.
"""

import os
import shutil
from collections.abc import Iterator, Mapping
from pathlib import Path, PurePosixPath

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
        _remove(entry)


def sync_tracked_files(folder: Path, files: Mapping[str, str]) -> None:
    """Makes the tracked files of `folder` exactly `files`, text by relative POSIX path, as
    `Workspace.sync_folder` describes: equal files keep their modification time, so build tools
    that compare timestamps skip them, and what the tools wrote (untracked entries) stays."""
    folder.parent.mkdir(parents=True, exist_ok=True)
    _ensure_directory(folder)
    tracked = [entry for entry in _entries(folder, folder) if not _untracked(folder, entry)]
    directories = [entry for entry in tracked if entry.is_dir() and not entry.is_symlink()]
    for entry in tracked:
        if _is_stale(folder, entry, files):
            entry.unlink()
    for directory in reversed(directories):
        if not any(directory.iterdir()):
            directory.rmdir()
    for path, text in files.items():
        _write_if_changed(folder, path, text)


def _is_stale(folder: Path, entry: Path, files: Mapping[str, str]) -> bool:
    """A link, or anything but a directory that `files` does not name."""
    if entry.is_symlink():
        return True
    return not entry.is_dir() and entry.relative_to(folder).as_posix() not in files


def _write_if_changed(folder: Path, path: str, text: str) -> None:
    """Writes `text` to `folder / path` unless that file holds it already; a link, or a directory
    or anything else that is not a plain file, is removed from the way first, never followed."""
    directory = folder
    for name in PurePosixPath(path).parent.parts:
        directory = directory / name
        _ensure_directory(directory)
    target = folder / path
    content = text.encode()
    if target.is_file() and not target.is_symlink():
        if target.read_bytes() == content:
            return
    elif os.path.lexists(target):
        _remove(target)
    target.write_bytes(content)


def _ensure_directory(path: Path) -> None:
    """Makes `path` a directory; a link or a file there is removed first, never followed."""
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        path.unlink()
    path.mkdir(exist_ok=True)


def _remove(entry: Path) -> None:
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
        module = (root / found.folder / GO_MODULE_FILE).read_text(
            encoding="utf-8", errors="replace"
        )
        for file in toolchain_files(Language.GO, module):
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
