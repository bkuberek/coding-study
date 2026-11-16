"""`LanguageFolders` on the local filesystem: the template folders of a workspace's languages
(docs/specs/cli.md#deleting-a-languages-folder)."""

import os
import shutil
from pathlib import Path

from coding_study.domain.errors import FolderNotDeletedError


class FsLanguageFolders:
    def __init__(self, root: Path) -> None:
        """`root` is the workspace root; every path is relative to it."""
        self._root = root

    def present(self, path: str) -> bool:
        return os.path.lexists(self._root / path)

    def leaves_workspace(self, path: str) -> bool:
        target = self._root / path
        return target.is_symlink() or not target.resolve().is_relative_to(self._root.resolve())

    def delete(self, path: str) -> None:
        target = self._root / path
        if target.is_symlink() or target.is_file():
            target.unlink(missing_ok=True)
            return
        if not target.is_dir():
            return
        stays: list[tuple[str, OSError]] = []

        def keep(_function: object, failed: str, error: BaseException) -> None:
            if isinstance(error, OSError):
                stays.append((failed, error))

        shutil.rmtree(target, onexc=keep)
        if stays:
            failed, error = stays[0]
            named = Path(failed).relative_to(self._root).as_posix()
            reason = (error.strerror or type(error).__name__).lower()
            raise FolderNotDeletedError(
                f"could not delete {named}: {reason}; the rest of {path}/ is deleted"
            )
