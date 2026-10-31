"""`Workspace` on the local filesystem; paths are repository-relative POSIX strings."""

import hashlib
import shutil
from contextlib import AbstractContextManager
from pathlib import Path

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.project_folders import remove_untracked, tracked_files

_MISSING = b"\0missing"


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

    def locked(self, path: str) -> AbstractContextManager[None]:
        return exclusive_lock(self.absolute(path))

    def tracked_files(self, path: str) -> tuple[str, ...]:
        folder = self.absolute(path)
        return tuple(sorted(file.relative_to(folder).as_posix() for file in tracked_files(folder)))

    def absolute(self, path: str) -> Path:
        return self._root / path
