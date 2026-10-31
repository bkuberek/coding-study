"""A folder's files as `cstudy test --watch`, `code_hash` and archives see them: the tracked ones,
without the `.venv` link, `node_modules`, caches and `uv.lock` that tools write
(docs/specs/installation-and-workspaces.md#project-folders).

A link to a directory is never followed, so no walk leaves the folder through the `.venv` link,
and removing that link never deletes the shared venv it points to.
"""

import shutil
from collections.abc import Iterator
from pathlib import Path

from coding_study.domain.workspace_projects import is_untracked


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
