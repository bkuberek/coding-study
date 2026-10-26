"""`Workspace` on the local filesystem; paths are repository-relative POSIX strings."""

import hashlib
import shutil
from pathlib import Path

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

    def content_hash(self, path: str) -> str:
        target = self.absolute(path)
        digest = hashlib.sha256()
        if target.is_dir():
            for file in sorted(entry for entry in target.rglob("*") if entry.is_file()):
                digest.update(file.relative_to(target).as_posix().encode())
                digest.update(file.read_bytes())
        else:
            digest.update(target.read_bytes() if target.is_file() else _MISSING)
        return digest.hexdigest()

    def absolute(self, path: str) -> Path:
        return self._root / path
