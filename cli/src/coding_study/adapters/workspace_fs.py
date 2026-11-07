"""`Workspace` on the local filesystem; paths are repository-relative POSIX strings."""

import errno
import hashlib
import os
import secrets
import shutil
import stat
import time
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import AbstractContextManager, ExitStack, contextmanager, suppress
from pathlib import Path, PurePosixPath

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.project_folders import (
    remove_untracked,
    sync_tracked_files,
    tracked_files,
    tracked_links,
)
from coding_study.domain.errors import LockBusyError
from coding_study.domain.project import PATH_SEPARATOR, relative_path_issue

_MISSING = b"\0missing"
_FOLDER_FLAGS = os.O_RDONLY | os.O_DIRECTORY
"""The folder itself may be a link, as `write_within` allows."""
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
"""Non-blocking, so opening a named pipe returns at once and is then refused."""
_NEW_FILE_MODE = 0o644
_NEW_DIRECTORY_MODE = 0o755
_TEMPORARY_PREFIX = ".cstudy-write-"
_TEMPORARY_NAME_BYTES = 8
_LOCK_POLL_S = 0.05


class WorkspaceFs:
    def __init__(self, root: Path) -> None:
        self._root = root

    def exists(self, path: str) -> bool:
        return self.absolute(path).exists()

    def read_text(self, path: str) -> str:
        return self.absolute(path).read_text(encoding="utf-8")

    def write_text(self, path: str, text: str) -> None:
        target = self.absolute(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def move_into(self, path: str, directory: str) -> str:
        source = self.absolute(path)
        destination = self.absolute(directory)
        destination.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination / source.name)
        return f"{directory}/{source.name}"

    def archive_folder(self, path: str, destination: str) -> None:
        target = self.absolute(destination)
        if target.exists():
            raise FileExistsError(f"{destination} already exists")
        source = self.absolute(path)
        remove_untracked(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)

    def remove_folder(self, path: str) -> None:
        folder = self.absolute(path)
        if folder.is_symlink():
            folder.unlink()
        elif folder.is_dir():
            shutil.rmtree(folder)

    def entries(self, path: str) -> tuple[str, ...]:
        directory = self.absolute(path)
        return (
            tuple(sorted(entry.name for entry in directory.iterdir())) if directory.is_dir() else ()
        )

    def leaving_entry(self, path: str) -> str | None:
        root = self._root.resolve()
        target = self.absolute(path)
        if not target.resolve().is_relative_to(root):
            return path
        if target.is_symlink() or not target.is_dir():
            return None
        for folder, directories, names in os.walk(target):
            for entry in (Path(folder) / name for name in (*directories, *names)):
                if entry.is_symlink() and not entry.resolve().is_relative_to(root):
                    return entry.relative_to(self._root).as_posix()
        return None

    def remove_entry(self, path: str) -> None:
        target = self.absolute(path)
        if target.is_symlink() or target.is_file():
            target.unlink(missing_ok=True)
        elif target.is_dir():
            shutil.rmtree(target)

    def ensure_link(self, path: str, target: str) -> bool:
        link = self.absolute(path)
        if link.exists():
            return False
        if link.is_symlink():
            link.unlink()
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target, target_is_directory=True)
        return True

    def content_hash(self, path: str) -> str:
        target = self.absolute(path)
        digest = hashlib.sha256()
        if target.is_symlink():
            digest.update(target.readlink().as_posix().encode())
        elif target.is_dir():
            for file in tracked_files(target):
                digest.update(file.relative_to(target).as_posix().encode())
                digest.update(file.read_bytes())
            for link in tracked_links(target):
                digest.update(link.relative_to(target).as_posix().encode())
                digest.update(link.readlink().as_posix().encode())
        else:
            digest.update(target.read_bytes() if target.is_file() else _MISSING)
        return digest.hexdigest()

    def write_within(self, folder: str, path: str, text: str) -> None:
        """Renames a new file over the old one, so a reader sees either, never a part."""
        *directories, name = _segments(path)
        with ExitStack() as descriptors:
            directory = self._walk(descriptors, folder, directories, _made_directory)
            mode = _replaced_mode(directory, name, path)
            _replace(directory, name, text.encode(), mode)

    def read_within(self, folder: str, path: str) -> bytes:
        *directories, name = _segments(path)
        with ExitStack() as descriptors:
            directory = self._walk(descriptors, folder, directories, _opened_directory)
            file = _kept(descriptors, _open_entry(directory, name, path, _FILE_FLAGS))
            _require_regular_file(os.fstat(file).st_mode, path)
            with os.fdopen(file, "rb", closefd=False) as reader:
                return reader.read()

    def delete_within(self, folder: str, path: str) -> None:
        *directories, name = _segments(path)
        with ExitStack() as descriptors:
            directory = self._walk(descriptors, folder, directories, _opened_directory)
            _require_regular_file(_entry_mode(directory, name), path)
            os.unlink(name, dir_fd=directory)

    def move_within(self, folder: str, path: str, target: str) -> None:
        """Links the file at `target`, which fails when anything is there, then unlinks `path`;
        a link that is the same file under another case of its name is a rename."""
        *source_directories, source_name = _segments(path)
        *target_directories, target_name = _segments(target)
        with ExitStack() as descriptors:
            source = self._walk(descriptors, folder, source_directories, _opened_directory)
            _require_regular_file(_entry_mode(source, source_name), path)
            destination = self._walk(descriptors, folder, target_directories, _made_directory)
            try:
                os.link(
                    source_name,
                    target_name,
                    src_dir_fd=source,
                    dst_dir_fd=destination,
                    follow_symlinks=False,
                )
            except FileExistsError:
                if not _same_file(source, source_name, destination, target_name):
                    raise
                os.rename(source_name, target_name, src_dir_fd=source, dst_dir_fd=destination)
                return
            os.unlink(source_name, dir_fd=source)

    def locked(self, path: str) -> AbstractContextManager[None]:
        return exclusive_lock(self.absolute(path))

    def locked_with_deadline(self, path: str, deadline_s: float) -> AbstractContextManager[None]:
        return _lock_with_deadline(self.absolute(path), path, deadline_s)

    def tracked_files(self, path: str) -> tuple[str, ...]:
        folder = self.absolute(path)
        return tuple(sorted(file.relative_to(folder).as_posix() for file in tracked_files(folder)))

    def absolute(self, path: str) -> Path:
        return self._root / path

    def sync_folder(self, path: str, files: Mapping[str, str]) -> None:
        sync_tracked_files(self.absolute(path), files)

    def _walk(
        self,
        descriptors: ExitStack,
        folder: str,
        directories: Sequence[str],
        enter: Callable[[int, str, PurePosixPath], int],
    ) -> int:
        """The last of `directories` under `folder`, open: each is entered by `enter` relative to
        the one before and never through a link, so no link swapped in after a check can lead
        outside `folder`."""
        directory = _kept(descriptors, os.open(self.absolute(folder), _FOLDER_FLAGS))
        for depth, name in enumerate(directories, start=1):
            step = PurePosixPath(*directories[:depth])
            directory = _kept(descriptors, enter(directory, name, step))
        return directory


def _segments(path: str) -> list[str]:
    """Raises ValueError for a path that is not relative and canonical, such as one with `..`."""
    issue = relative_path_issue(path)
    if issue is not None:
        raise ValueError(f"{path} {issue}")
    return path.split(PATH_SEPARATOR)


def _kept(descriptors: ExitStack, descriptor: int) -> int:
    """`descriptor`, closed when `descriptors` closes."""
    descriptors.callback(os.close, descriptor)
    return descriptor


def _opened_directory(directory: int, name: str, step: PurePosixPath) -> int:
    return _open_entry(directory, name, step, _DIRECTORY_FLAGS)


def _made_directory(directory: int, name: str, step: PurePosixPath) -> int:
    """The directory `name` of the open `directory`, made first when missing."""
    with suppress(FileExistsError):
        os.mkdir(name, _NEW_DIRECTORY_MODE, dir_fd=directory)
    return _opened_directory(directory, name, step)


def _open_entry(directory: int, name: str, step: PurePosixPath | str, flags: int) -> int:
    """Opens the entry `name` of the open `directory` without following a link; raises
    ValueError naming `step` when it is a link or, for a directory on the way, not one."""
    try:
        return os.open(name, flags, dir_fd=directory)
    except OSError as error:
        if error.errno not in (errno.ELOOP, errno.ENOTDIR):
            raise
        entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if stat.S_ISLNK(entry.st_mode):
        raise ValueError(f"{step} is a symbolic link")
    raise ValueError(f"{step} is not a directory")


def _entry_mode(directory: int, name: str) -> int:
    """The mode of the entry `name` itself, a link included; FileNotFoundError when missing."""
    return os.stat(name, dir_fd=directory, follow_symlinks=False).st_mode


def _require_regular_file(mode: int, path: str) -> None:
    if stat.S_ISLNK(mode):
        raise ValueError(f"{path} is a symbolic link")
    if stat.S_ISDIR(mode):
        raise ValueError(f"{path} is a directory")
    if not stat.S_ISREG(mode):
        raise ValueError(f"{path} is not a regular file")


def _replaced_mode(directory: int, name: str, path: str) -> int:
    """The mode the file `name` keeps when a write replaces it; a new file's when it is missing."""
    try:
        mode = _entry_mode(directory, name)
    except FileNotFoundError:
        return _NEW_FILE_MODE
    _require_regular_file(mode, path)
    return stat.S_IMODE(mode)


def _replace(directory: int, name: str, content: bytes, mode: int) -> None:
    """Writes `content` to a new file in `directory` and renames it to `name`."""
    temporary = f"{_TEMPORARY_PREFIX}{secrets.token_hex(_TEMPORARY_NAME_BYTES)}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, mode, dir_fd=directory)
    try:
        with os.fdopen(descriptor, "wb") as file:
            os.fchmod(file.fileno(), mode)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=directory)
        raise


def _same_file(source: int, source_name: str, target: int, target_name: str) -> bool:
    """Whether two entries are one file, as two cases of a name are where case is ignored."""
    return os.path.samestat(
        os.stat(source_name, dir_fd=source, follow_symlinks=False),
        os.stat(target_name, dir_fd=target, follow_symlinks=False),
    )


class _BusyError(Exception):
    """The lock was held when it was asked for."""


def _refuse_to_wait() -> None:
    raise _BusyError


@contextmanager
def _lock_with_deadline(lock: Path, path: str, deadline_s: float) -> Generator[None]:
    """`exclusive_lock` on `lock`, asked for again every `_LOCK_POLL_S` until it is free or
    `deadline_s` has passed: `flock` itself cannot wait with a deadline."""
    give_up_at = time.monotonic() + deadline_s
    with ExitStack() as held:
        while not _entered(held, lock):
            remaining = give_up_at - time.monotonic()
            if remaining <= 0:
                raise LockBusyError(path, deadline_s)
            time.sleep(min(_LOCK_POLL_S, remaining))
        yield


def _entered(held: ExitStack, lock: Path) -> bool:
    try:
        held.enter_context(exclusive_lock(lock, on_wait=_refuse_to_wait))
    except _BusyError:
        return False
    return True
