"""A project problem's reference as `cstudy solution` shows it (docs/specs/cli.md#cstudy-solution):
each file the overlay adds in full, and each file it changes as a unified diff against the
starter's file.
"""

from dataclasses import dataclass
from difflib import unified_diff

from coding_study.domain.project import PATH_SEPARATOR, ProjectTree

STARTER_PREFIX = "starter"
REFERENCE_PREFIX = "reference"


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
    files: list[ReferenceFile] = []
    for file in overlay.files:
        before = starter.file(file.path) if starter else None
        text = file.text or ""
        if before is None:
            files.append(ReferenceFile(file.path, True, text))
            continue
        diff = _diff(file.path, before.text or "", text)
        if diff:
            files.append(ReferenceFile(file.path, False, diff))
    return tuple(files)


def _diff(path: str, before: str, after: str) -> str:
    lines = unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"{STARTER_PREFIX}{PATH_SEPARATOR}{path}",
        tofile=f"{REFERENCE_PREFIX}{PATH_SEPARATOR}{path}",
    )
    return "".join(line if line.endswith("\n") else f"{line}\n" for line in lines)
