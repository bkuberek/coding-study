"""Raw files of problem directories (`<slug>/`), for checks that go beyond meta.yaml."""

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from coding_study.adapters.fs_problem_repository import (
    META_FILE,
    PROBLEMS_DIRECTORY,
    parse_yaml,
)
from coding_study.domain.errors import ContentError, UnknownProblemError
from coding_study.domain.problem import SLUG_PATTERN
from coding_study.domain.problem_files import MisnamedDirectory, misnamed_directory


class FsProblemFiles:
    """`ProblemFiles` for one problems directory under the repository root."""

    def __init__(self, root: Path, directory: str = PROBLEMS_DIRECTORY) -> None:
        self._root = root
        self._directory = directory

    @property
    def directory(self) -> str:
        return self._directory

    def slugs(self) -> tuple[str, ...]:
        """The name of every directory named by a slug, in name order."""
        return tuple(entry.name for entry in self._entries() if SLUG_PATTERN.fullmatch(entry.name))

    def misnamed(self) -> tuple[MisnamedDirectory, ...]:
        return tuple(
            misnamed_directory(entry.name, _meta_slug(entry))
            for entry in self._entries()
            if not SLUG_PATTERN.fullmatch(entry.name)
        )

    def problem_directory(self, slug: str) -> str:
        if slug not in self.slugs():
            raise UnknownProblemError(slug)
        return f"{self._directory}/{slug}"

    def read_text(self, slug: str, name: str) -> str | None:
        path = self.path(slug, name)
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def file_names(self, slug: str, directory: str = "") -> tuple[str, ...]:
        folder = self.path(slug, directory)
        if not folder.is_dir():
            return ()
        return tuple(sorted(entry.name for entry in folder.iterdir() if entry.is_file()))

    def path(self, slug: str, name: str) -> Path:
        return self._root / self.problem_directory(slug) / name

    def fingerprint(self, slug: str, names: Sequence[str]) -> str:
        digest = hashlib.sha256()
        for name in names:
            path = self.path(slug, name)
            digest.update(name.encode())
            digest.update(path.read_bytes() if path.is_file() else b"\0missing")
        return digest.hexdigest()

    def _entries(self) -> list[Path]:
        folder = self._root / self._directory
        if not folder.is_dir():
            return []
        return [entry for entry in sorted(folder.iterdir()) if entry.is_dir()]


def _meta_slug(directory: Path) -> object:
    """The `slug` of the directory's meta.yaml; None when there is no readable one."""
    source = f"{directory.name}/{META_FILE}"
    try:
        document = parse_yaml((directory / META_FILE).read_text(encoding="utf-8"), source)
    except (OSError, UnicodeDecodeError, ContentError):
        return None
    return cast(dict[str, object], document).get("slug") if isinstance(document, dict) else None
