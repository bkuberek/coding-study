"""The user's study guides on disk, under config `study_guides.root`.

Items reference guide files relative to that root
(docs/specs/content.md#non-autograded-item-format); a reference is linked only when its file
exists there.
"""

from pathlib import Path, PurePosixPath
from typing import Self

HOME_PREFIX = "~/"
PARENT_DIRECTORY = ".."


class FsStudyGuides:
    """`StudyGuides` for one root directory; `None` when no root is configured."""

    def __init__(self, root: Path | None) -> None:
        self._root = root

    @classmethod
    def from_setting(cls, root: str | None, home: Path) -> Self:
        """`root` as the config holds it: absolute, or relative to `home` after `~/`."""
        if root is None:
            return cls(None)
        if root.startswith(HOME_PREFIX):
            return cls(home / root.removeprefix(HOME_PREFIX))
        return cls(Path(root))

    def locate(self, path: str) -> str | None:
        relative = PurePosixPath(path)
        if self._root is None or relative.is_absolute() or PARENT_DIRECTORY in relative.parts:
            return None
        guide = (self._root / relative).absolute()
        return guide.as_uri() if guide.is_file() else None
