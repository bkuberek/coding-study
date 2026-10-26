"""`ProblemTemplates` shipped with the package, in `templates/<template>/` next to this module.

Shipping them as package data (like the SQLite migrations) keeps `cstudy new` working for any
repository root, including one set by `CS_ROOT`.
"""

from collections.abc import Iterator
from importlib import resources
from importlib.resources.abc import Traversable

TEMPLATES_PACKAGE = "coding_study.adapters"
TEMPLATES_DIRECTORY = "templates"
IGNORED_DIRECTORIES = frozenset({"__pycache__"})


class PackagedProblemTemplates:
    def files(self, template: str) -> dict[str, str]:
        directory = resources.files(TEMPLATES_PACKAGE) / TEMPLATES_DIRECTORY / template
        return {path: entry.read_text(encoding="utf-8") for path, entry in _walk(directory, "")}


def _walk(directory: Traversable, prefix: str) -> Iterator[tuple[str, Traversable]]:
    for entry in sorted(directory.iterdir(), key=lambda found: found.name):
        path = f"{prefix}{entry.name}"
        if entry.is_dir():
            if entry.name not in IGNORED_DIRECTORIES:
                yield from _walk(entry, f"{path}/")
        else:
            yield path, entry
