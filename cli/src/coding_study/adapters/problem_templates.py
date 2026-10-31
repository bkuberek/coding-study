"""`ProblemTemplates` shipped with the package, in `templates/<template>/` next to this module.

Shipping them as package data (like the SQLite migrations) keeps `cstudy new` working for any
repository root, including one set by `CS_ROOT`. A file that tools would read where it ships
ends in `.tmpl`, which its path in the new problem drops: a project starter's `pyproject.toml`,
which ruff would take for the configuration of the templates, and code whose placeholders keep it
from being valid until they are filled in, such as `class {{class_name}}:` in Python.
"""

from collections.abc import Iterator
from importlib import resources
from importlib.resources.abc import Traversable

TEMPLATES_PACKAGE = "coding_study.adapters"
TEMPLATES_DIRECTORY = "templates"
IGNORED_DIRECTORIES = frozenset({"__pycache__", ".ruff_cache", ".pytest_cache"})
"""Caches that tools may leave in the shipped templates; never part of a new problem."""
TEMPLATE_SUFFIX = ".tmpl"


class PackagedProblemTemplates:
    def files(self, template: str) -> dict[str, str]:
        directory = resources.files(TEMPLATES_PACKAGE) / TEMPLATES_DIRECTORY / template
        return {
            path.removesuffix(TEMPLATE_SUFFIX): entry.read_text(encoding="utf-8")
            for path, entry in _walk(directory, "")
        }


def _walk(directory: Traversable, prefix: str) -> Iterator[tuple[str, Traversable]]:
    for entry in sorted(directory.iterdir(), key=lambda found: found.name):
        path = f"{prefix}{entry.name}"
        if entry.is_dir():
            if entry.name not in IGNORED_DIRECTORIES:
                yield from _walk(entry, f"{path}/")
        else:
            yield path, entry
