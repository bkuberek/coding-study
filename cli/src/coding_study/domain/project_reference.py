"""A project problem's reference as `cstudy solution` shows it (docs/specs/cli.md#cstudy-solution):
each file the overlay adds in full, and each file it changes as a unified diff against the
starter's file. A broken overlay shows the same way against the reference: the starter with the
reference's overlay over it.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from difflib import unified_diff

from coding_study.domain.project import PATH_SEPARATOR, ProjectFile, ProjectTree

STARTER_PREFIX = "starter"
REFERENCE_PREFIX = "reference"
BROKEN_PREFIX = "broken"


@dataclass(frozen=True, slots=True)
class ReferenceFile:
    path: str
    """Relative to the project folder."""
    added: bool
    """True: the starter has no such file, and `text` is the file; False: `text` is a diff."""
    text: str


def reference_files(starter: ProjectTree | None, overlay: ProjectTree) -> tuple[ReferenceFile, ...]:
    """The overlay's files in path order; a file the overlay leaves as the starter has it is left
    out. A file that is not text shows as empty."""
    return _Changes(STARTER_PREFIX, REFERENCE_PREFIX).of(starter, overlay)


def broken_files(
    starter: ProjectTree | None, reference: ProjectTree | None, broken: ProjectTree
) -> tuple[ReferenceFile, ...]:
    """A broken overlay's files as `reference_files` shows a reference's, against the starter
    with the reference's overlay over it."""
    base = _over(starter.files if starter else (), reference.files if reference else ())
    return _Changes(REFERENCE_PREFIX, BROKEN_PREFIX).of(base, broken)


def _over(below: Iterable[ProjectFile], above: Iterable[ProjectFile]) -> ProjectTree:
    files = {file.path: file for file in below} | {file.path: file for file in above}
    return ProjectTree(tuple(files[path] for path in sorted(files)))


@dataclass(frozen=True, slots=True)
class _Changes:
    before: str
    after: str
    """The diff headers' prefixes: `starter/` and `reference/`, or `reference/` and `broken/`."""

    def of(self, base: ProjectTree | None, overlay: ProjectTree) -> tuple[ReferenceFile, ...]:
        files: list[ReferenceFile] = []
        for file in overlay.files:
            before = base.file(file.path) if base else None
            text = file.text or ""
            if before is None:
                files.append(ReferenceFile(file.path, True, text))
                continue
            diff = self._diff(file.path, before.text or "", text)
            if diff:
                files.append(ReferenceFile(file.path, False, diff))
        return tuple(files)

    def _diff(self, path: str, before: str, after: str) -> str:
        lines = unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"{self.before}{PATH_SEPARATOR}{path}",
            tofile=f"{self.after}{PATH_SEPARATOR}{path}",
        )
        return "".join(line if line.endswith("\n") else f"{line}\n" for line in lines)
