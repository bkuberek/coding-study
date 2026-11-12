"""The concept guides and learning paths in guides/ (docs/specs/guides.md).

Every directory directly inside `guides/` but `paths/` is a guide; every `*.yaml` in
`guides/paths/` is a path. Hidden entries and `__pycache__` are left out, as a checkout may hold
them. The schemas load on first use, so a content root that has no guides never reads them.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from coding_study.adapters.fs_problem_repository import parse_yaml, read_content_file
from coding_study.adapters.schema_validation import SCHEMAS_DIRECTORY, SchemaValidator
from coding_study.domain.concept_guides import (
    DIAGRAMS_DIRECTORY,
    EXAMPLES_DIRECTORY,
    GUIDE_FILE,
    GUIDE_META_FILE,
    GUIDES_DIRECTORY,
    PATH_SUFFIX,
    PATHS_DIRECTORY,
    GuideLevel,
    GuideMeta,
    LearningPath,
    PathStep,
)
from coding_study.domain.errors import ContentError

GUIDE_SCHEMA_FILE = "guide.schema.json"
PATH_SCHEMA_FILE = "path.schema.json"
_SKIPPED_NAMES = ("__pycache__",)
_HIDDEN_PREFIX = "."


class FsGuideCatalog:
    """`GuideCatalog` for the guides/ directory under a content root."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._guides = root / GUIDES_DIRECTORY
        self._paths = self._guides / PATHS_DIRECTORY
        self._validators: dict[str, SchemaValidator] = {}

    def slugs(self) -> tuple[str, ...]:
        if not self._guides.is_dir():
            return ()
        return tuple(
            entry.name
            for entry in _visible(self._guides)
            if entry.is_dir() and entry.name != PATHS_DIRECTORY
        )

    def guide_directory(self, slug: str) -> str:
        return f"{GUIDES_DIRECTORY}/{slug}"

    def load(self, slug: str) -> GuideMeta:
        document = self._validated(self._guides / slug / GUIDE_META_FILE, GUIDE_SCHEMA_FILE)
        return GuideMeta(
            slug=slug,
            title=document["title"],
            summary=document["summary"],
            level=GuideLevel(document["level"]),
            prerequisites=tuple(document.get("prerequisites", ())),
            related=tuple(document.get("related", ())),
            problems=tuple(document.get("problems", ())),
        )

    def read_guide(self, slug: str) -> str | None:
        path = self._guides / slug / GUIDE_FILE
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def files(self, slug: str) -> tuple[str, ...]:
        folder = self._guides / slug
        return tuple(sorted(path.relative_to(folder).as_posix() for path in _files_under(folder)))

    def examples(self, slug: str) -> Mapping[str, str]:
        folder = self._guides / slug
        return {
            path.relative_to(folder).as_posix(): path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(_files_under(folder / EXAMPLES_DIRECTORY))
        }

    def diagrams(self, slug: str) -> Mapping[str, str]:
        folder = self._guides / slug
        return {
            path.relative_to(folder).as_posix(): path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(_files_under(folder / DIAGRAMS_DIRECTORY))
        }

    def examples_folder(self, slug: str) -> Path:
        return self._guides / slug / EXAMPLES_DIRECTORY

    def path_slugs(self) -> tuple[str, ...]:
        if not self._paths.is_dir():
            return ()
        return tuple(
            entry.name.removesuffix(PATH_SUFFIX)
            for entry in _visible(self._paths)
            if entry.is_file() and entry.name.endswith(PATH_SUFFIX)
        )

    def path_file(self, slug: str) -> str:
        return f"{GUIDES_DIRECTORY}/{PATHS_DIRECTORY}/{slug}{PATH_SUFFIX}"

    def load_path(self, slug: str) -> LearningPath:
        document = self._validated(self._paths / f"{slug}{PATH_SUFFIX}", PATH_SCHEMA_FILE)
        return LearningPath(
            slug=slug,
            title=document["title"],
            summary=document["summary"],
            steps=tuple(_step(step) for step in document["steps"]),
        )

    def _validated(self, path: Path, schema_file: str) -> Any:
        source = path.relative_to(self._root).as_posix()
        document = parse_yaml(read_content_file(path, source), source)
        issues = self._validator(schema_file).violations(document, source)
        if issues:
            raise ContentError(issues)
        return document

    def _validator(self, schema_file: str) -> SchemaValidator:
        if schema_file not in self._validators:
            path = self._root / SCHEMAS_DIRECTORY / schema_file
            self._validators[schema_file] = SchemaValidator.from_file(path)
        return self._validators[schema_file]


def _step(document: Mapping[str, Any]) -> PathStep:
    if "guide" in document:
        return PathStep.guide(document["guide"])
    return PathStep.problem(document["problem"], document.get("level"))


def _visible(folder: Path) -> list[Path]:
    return [
        entry
        for entry in sorted(folder.iterdir())
        if not entry.name.startswith(_HIDDEN_PREFIX) and entry.name not in _SKIPPED_NAMES
    ]


def _files_under(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    found: list[Path] = []
    for entry in _visible(folder):
        if entry.is_dir():
            found.extend(_files_under(entry))
        elif entry.is_file():
            found.append(entry)
    return found
