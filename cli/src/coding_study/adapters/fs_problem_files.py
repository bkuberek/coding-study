"""Raw files of problem directories (`<id>-<slug>/`), for checks that go beyond meta.yaml."""

import hashlib
from collections.abc import Sequence
from pathlib import Path

from coding_study.adapters.fs_problem_repository import PROBLEMS_DIRECTORY
from coding_study.domain.errors import UnknownProblemError

ID_DIGITS = 4


def slug_of_directory(directory_name: str) -> str | None:
    """The slug of an `<id>-<slug>` directory name, or None for any other name."""
    prefix, separator, slug = directory_name.partition("-")
    if separator and len(prefix) == ID_DIGITS and prefix.isdigit():
        return slug
    return None


class FsProblemFiles:
    """`ProblemFiles` for one problems directory under the repository root."""

    def __init__(self, root: Path, directory: str = PROBLEMS_DIRECTORY) -> None:
        self._root = root
        self._directory = directory

    @property
    def directory(self) -> str:
        return self._directory

    def slugs(self) -> tuple[str, ...]:
        """One slug per directory, so a duplicated slug appears twice."""
        return tuple(slug for slug, _ in self._directories())

    def directory_names(self) -> tuple[str, ...]:
        return tuple(name for _, name in self._directories())

    def problem_directory(self, slug: str) -> str:
        """The first directory with this slug, like `FsProblemRepository.load`."""
        name = next((name for found, name in self._directories() if found == slug), None)
        if name is None:
            raise UnknownProblemError(slug)
        return f"{self._directory}/{name}"

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

    def _directories(self) -> list[tuple[str, str]]:
        """(slug, directory name) pairs in directory name order."""
        folder = self._root / self._directory
        if not folder.is_dir():
            return []
        return [
            (slug, entry.name)
            for entry in sorted(folder.iterdir())
            if entry.is_dir() and (slug := slug_of_directory(entry.name)) is not None
        ]
