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
import stat
from collections.abc import Iterator, Mapping
from contextlib import suppress
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
_SETUID_BITS = stat.S_ISUID | stat.S_ISGID
PYPROJECT_FILE = "pyproject.toml"
SERVICE_TRACKED_LOCK = "uv.lock"
_PROJECT_TABLE = "[project]"
PLAIN_FILE_LIMIT_BYTES = 1024 * 1024
"""Past any `pyproject.toml` or `go.mod`, and a bound on what sandboxed code can make cstudy hold."""
_PLAIN_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
"""Non-blocking, so opening a named pipe returns at once and is then refused."""


def tracked_files(folder: Path) -> list[Path]:
    """Every tracked file under `folder`, in path order; none when it is not a directory. A link
    is no file here: sandboxed code can leave one that names anything on your machine, and what it
    names is never read."""
    if not folder.is_dir():
        return []
    return sorted(
        entry
        for entry in _entries(folder, folder)
        if entry.is_file() and not entry.is_symlink() and not _untracked(folder, entry)
    )


def tracked_links(folder: Path) -> list[Path]:
    """Every link under `folder` outside the untracked entries, in path order: what `code_hash`
    takes the target of, as text."""
    if not folder.is_dir():
        return []
    return sorted(
        entry
        for entry in _entries(folder, folder)
        if entry.is_symlink() and not _untracked(folder, entry)
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
    """A service project's `uv.lock` is a file grading trusts, not tool output."""
    relative = entry.relative_to(folder).as_posix()
    if relative == SERVICE_TRACKED_LOCK and declares_its_project(folder):
        return False
    return is_untracked(relative)


def declares_its_project(folder: Path) -> bool:
    """Whether the folder's `pyproject.toml` has a `[project]` table: only a service project's does,
    since S15 refuses one in any other starter, for the sake of the `.venv` link."""
    text = _plain_text(folder / PYPROJECT_FILE)
    return text is not None and _PROJECT_TABLE in text.splitlines()


def _plain_text(path: Path) -> str | None:
    """The start of the regular file at `path`. A file in a project folder can be anything sandboxed
    code left there, so a link, a named pipe, a device or a directory is no such file: None, and
    what it names is never read."""
    try:
        descriptor = os.open(path, _PLAIN_FILE_FLAGS)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return None
        return os.read(descriptor, PLAIN_FILE_LIMIT_BYTES).decode("utf-8", errors="replace")
    except OSError:
        return None
    finally:
        os.close(descriptor)


def clear_setuid_bits(folder: Path) -> None:
    """Takes the setuid and setgid bits off every regular file under `folder`, which sandboxed code
    can set and a host tool would obey; a link is never followed."""
    for directory, _directories, names in os.walk(folder, followlinks=False):
        for name in names:
            with suppress(OSError):
                _clear_setuid_bit(Path(directory) / name)


def _clear_setuid_bit(path: Path) -> None:
    mode = os.lstat(path).st_mode
    if not stat.S_ISREG(mode) or not mode & _SETUID_BITS:
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fchmod(descriptor, stat.S_IMODE(mode) & ~_SETUID_BITS)
    finally:
        os.close(descriptor)


def go_project_folders(root: Path) -> tuple[GoProjectFolder, ...]:
    """Every folder in the workspace `root`'s `projects/` that holds a `go.mod`, in name order."""
    projects = root / PROJECTS_DIRECTORY
    if not projects.is_dir():
        return ()
    modules = (
        (folder, _plain_text(folder / GO_MODULE_FILE)) for folder in sorted(projects.iterdir())
    )
    return tuple(_go_folder(folder, text) for folder, text in modules if text is not None)


def write_missing_go_work_files(root: Path) -> tuple[str, ...]:
    """Writes the `go.work` of each Go folder that lacks one; returns those folders. A link there,
    dangling or not, is sandboxed code's or yours, and no write goes through it."""
    written: list[str] = []
    for found in go_project_folders(root):
        if found.has_work_file:
            continue
        module = _plain_text(root / found.folder / GO_MODULE_FILE)
        paths = {
            root / found.folder / file.path: file.text
            for file in toolchain_files(Language.GO, module)
        }
        missing = {path: text for path, text in paths.items() if not os.path.lexists(path)}
        for path, text in missing.items():
            path.write_text(text, encoding="utf-8")
        if missing:
            written.append(found.folder)
    return tuple(written)


def _go_folder(folder: Path, text: str) -> GoProjectFolder:
    module = go_module_file(text)
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
