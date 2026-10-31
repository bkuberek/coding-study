"""`Workspace` on the local filesystem; paths are repository-relative POSIX strings."""

import errno
import hashlib
import os
import shutil
import stat
from collections.abc import Mapping
from contextlib import AbstractContextManager, ExitStack
from pathlib import Path, PurePosixPath

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.project_folders import (
    remove_untracked,
    sync_tracked_files,
    tracked_files,
)

_MISSING = b"\0missing"
_FOLDER_FLAGS = os.O_RDONLY | os.O_DIRECTORY
"""The folder itself may be a link, as `write_within` allows."""
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
"""Non-blocking, so opening a named pipe returns at once and is then refused."""


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
        if target.is_dir():
            for file in tracked_files(target):
                digest.update(file.relative_to(target).as_posix().encode())
                digest.update(file.read_bytes())
        else:
            digest.update(target.read_bytes() if target.is_file() else _MISSING)
        return digest.hexdigest()

    def write_within(self, folder: str, path: str, text: str) -> None:
        root = self.absolute(folder)
        segments = PurePosixPath(path).parts
        for depth in range(1, len(segments) + 1):
            _refuse_unsafe(root, PurePosixPath(*segments[:depth]), depth == len(segments))
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def read_within(self, folder: str, path: str) -> bytes:
        """Opens each directory on the way, then the file, relative to the one before and never
        following a link, so no link swapped in after a check can lead outside `folder`."""
        segments = PurePosixPath(path).parts
        with ExitStack() as descriptors:
            directory = _kept(descriptors, os.open(self.absolute(folder), _FOLDER_FLAGS))
            for depth, name in enumerate(segments[:-1], start=1):
                step = PurePosixPath(*segments[:depth])
                directory = _kept(descriptors, _open_entry(directory, name, step, _DIRECTORY_FLAGS))
            file = _kept(descriptors, _open_entry(directory, segments[-1], path, _FILE_FLAGS))
            mode = os.fstat(file).st_mode
            if stat.S_ISDIR(mode):
                raise ValueError(f"{path} is a directory")
            if not stat.S_ISREG(mode):
                raise ValueError(f"{path} is not a regular file")
            with os.fdopen(file, "rb", closefd=False) as reader:
                return reader.read()

    def locked(self, path: str) -> AbstractContextManager[None]:
        return exclusive_lock(self.absolute(path))

    def tracked_files(self, path: str) -> tuple[str, ...]:
        folder = self.absolute(path)
        return tuple(sorted(file.relative_to(folder).as_posix() for file in tracked_files(folder)))

    def absolute(self, path: str) -> Path:
        return self._root / path

    def sync_folder(self, path: str, files: Mapping[str, str]) -> None:
        sync_tracked_files(self.absolute(path), files)


def _kept(descriptors: ExitStack, descriptor: int) -> int:
    """`descriptor`, closed when `descriptors` closes."""
    descriptors.callback(os.close, descriptor)
    return descriptor


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


def _refuse_unsafe(root: Path, step: PurePosixPath, is_file: bool) -> None:
    """Raises ValueError when the entry `step`, under `root`, would make a write leave `root` or
    replace a directory: a link, a directory at the file's path, a file on the way."""
    entry = root / step
    if entry.is_symlink():
        raise ValueError(f"{step} is a symbolic link")
    if is_file and entry.is_dir():
        raise ValueError(f"{step} is a directory")
    if not is_file and entry.exists() and not entry.is_dir():
        raise ValueError(f"{step} is not a directory")
