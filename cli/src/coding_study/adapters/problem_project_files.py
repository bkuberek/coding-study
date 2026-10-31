"""The trees of a project problem: `starter/` and each directory in `solutions/`
(docs/specs/problem-format.md#project-problems).

Only plain files are listed. A symbolic link is refused wherever it points and never followed, so
no listed path leads out of its folder; a special file is refused without being read.
"""

from collections.abc import Iterator
from pathlib import Path

from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.problem_files import SOLUTIONS_DIRECTORY, STARTER_DIRECTORY
from coding_study.domain.project import ProjectFile, ProjectFiles, ProjectTree

LINK_REFUSED = "is a symbolic link: a project folder holds plain files only"
SPECIAL_FILE_REFUSED = "is not a plain file"
_NUL = b"\0"


def read_project_files(directory: Path, source: str) -> ProjectFiles:
    """The trees in the problem directory `directory`, which issues name `source`.

    Raises ContentError naming every symbolic link and special file in them.
    """
    reader = _TreeReader()
    starter = reader.tree(directory / STARTER_DIRECTORY, f"{source}/{STARTER_DIRECTORY}")
    solutions = directory / SOLUTIONS_DIRECTORY
    overlays = {
        folder.name: tree
        for folder in _overlay_folders(solutions)
        if (tree := reader.tree(folder, f"{source}/{SOLUTIONS_DIRECTORY}/{folder.name}"))
    }
    if reader.issues:
        raise ContentError(reader.issues)
    return ProjectFiles(starter, overlays)


def _overlay_folders(solutions: Path) -> list[Path]:
    """Every entry of `solutions/` that is a directory or a link, hidden ones aside."""
    if not solutions.is_dir():
        return []
    return [
        entry
        for entry in sorted(solutions.iterdir())
        if not entry.name.startswith(".") and (entry.is_dir() or entry.is_symlink())
    ]


class _TreeReader:
    def __init__(self) -> None:
        self.issues: list[ContentIssue] = []

    def tree(self, folder: Path, source: str) -> ProjectTree | None:
        """None when `folder` does not exist or is refused."""
        if folder.is_symlink():
            self._refuse(source, LINK_REFUSED)
            return None
        if not folder.is_dir():
            return None
        files: list[ProjectFile] = []
        for entry in _entries(folder):
            path = entry.relative_to(folder).as_posix()
            if entry.is_symlink():
                self._refuse(f"{source}/{path}", LINK_REFUSED)
            elif entry.is_file():
                files.append(_project_file(entry, path))
            else:
                self._refuse(f"{source}/{path}", SPECIAL_FILE_REFUSED)
        return ProjectTree(tuple(sorted(files, key=lambda file: file.path)))

    def _refuse(self, source: str, message: str) -> None:
        self.issues.append(ContentIssue(source, "", message))


def _entries(folder: Path) -> Iterator[Path]:
    """Everything under `folder` but its directories; links are listed, never followed."""
    for entry in sorted(folder.iterdir()):
        if entry.is_dir() and not entry.is_symlink():
            yield from _entries(entry)
        else:
            yield entry


def _project_file(file: Path, path: str) -> ProjectFile:
    content = file.read_bytes()
    return ProjectFile(path, len(content), _text(content))


def _text(content: bytes) -> str | None:
    if _NUL in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None
