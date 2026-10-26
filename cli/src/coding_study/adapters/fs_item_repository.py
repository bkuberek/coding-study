"""Loads non-autograded items from tracks/<track>/<slug>/ (docs/specs/content.md).

Every directory directly inside a track directory is an item; other entries (such as a track's
README.md) are ignored.
"""

from pathlib import Path
from typing import Any

from coding_study.adapters.document_index import DocumentIndex, file_stamp, index_key
from coding_study.adapters.fs_problem_repository import parse_yaml, read_content_file
from coding_study.adapters.schema_validation import (
    ITEM_SCHEMA_FILE,
    SCHEMAS_DIRECTORY,
    SchemaValidator,
)
from coding_study.domain.errors import ContentError, ContentIssue, UnknownProblemError
from coding_study.domain.items import ITEM_FILE, ItemMeta, ItemReferences
from coding_study.domain.problem import DEFAULT_CURRICULUM_ORDER, ContentStatus, Difficulty, Track

TRACKS_DIRECTORY = "tracks"
_HIDDEN_PREFIX = "."


class FsItemRepository:
    """`ItemRepository` for the tracks/ directory under the repository root."""

    def __init__(self, root: Path, index: DocumentIndex | None = None) -> None:
        self._root = root
        self._tracks = root / TRACKS_DIRECTORY
        self._index = index
        schema_file = root / SCHEMAS_DIRECTORY / ITEM_SCHEMA_FILE
        self._schema_stamp = file_stamp(schema_file)
        self._schema = SchemaValidator.from_file(schema_file)

    def slugs(self) -> tuple[str, ...]:
        return tuple(directory.name for directory in self._item_directories())

    def directories(self) -> tuple[str, ...]:
        return tuple(self._source(directory) for directory in self._item_directories())

    def item_directory(self, slug: str) -> str:
        return self._source(self._directory_of(slug))

    def load(self, slug: str) -> ItemMeta:
        return self._meta(self._directory_of(slug))

    def list_items(self) -> tuple[ItemMeta, ...]:
        items: list[ItemMeta] = []
        issues: list[ContentIssue] = []
        directories = self._item_directories()
        for directory in directories:
            try:
                items.append(self._meta(directory))
            except ContentError as error:
                issues.extend(error.issues)
        self._save_index(directories)
        if issues:
            raise ContentError(issues)
        return tuple(items)

    def read_text(self, slug: str, name: str) -> str | None:
        path = self._directory_of(slug) / name
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def file_names(self, slug: str, directory: str = "") -> tuple[str, ...]:
        folder = self._directory_of(slug) / directory
        if not folder.is_dir():
            return ()
        return tuple(sorted(entry.name for entry in folder.iterdir() if entry.is_file()))

    def _meta(self, directory: Path) -> ItemMeta:
        path = directory / ITEM_FILE
        source = self._source(path)
        document, issues = self._validated(path, source)
        if issues:
            raise ContentError(issues)
        meta = _item_meta(document)
        _check_location(directory, meta, source)
        return meta

    def _validated(self, path: Path, source: str) -> tuple[Any, list[ContentIssue]]:
        def read() -> tuple[Any, list[ContentIssue]]:
            document = parse_yaml(read_content_file(path, source), source)
            return document, self._schema.violations(document, source)

        if self._index is None:
            return read()
        return self._index.validated(index_key(path), path, self._schema_stamp, read)

    def _save_index(self, directories: list[Path]) -> None:
        if self._index is None:
            return
        self._index.retain(
            f"{index_key(self._tracks)}/", {index_key(d / ITEM_FILE) for d in directories}
        )
        self._index.save()

    def _directory_of(self, slug: str) -> Path:
        for directory in self._item_directories():
            if directory.name == slug:
                return directory
        raise UnknownProblemError(slug)

    def _item_directories(self) -> list[Path]:
        """Items in track directory order, then by name."""
        if not self._tracks.is_dir():
            return []
        return [
            item
            for track in _visible_directories(self._tracks)
            for item in _visible_directories(track)
        ]

    def _source(self, path: Path) -> str:
        return path.relative_to(self._root).as_posix()


def _visible_directories(parent: Path) -> list[Path]:
    return [
        entry
        for entry in sorted(parent.iterdir())
        if entry.is_dir() and not entry.name.startswith(_HIDDEN_PREFIX)
    ]


def _item_meta(document: Any) -> ItemMeta:
    references = document.get("references", {})
    return ItemMeta(
        slug=document["slug"],
        title=document["title"],
        track=Track(document["track"]),
        difficulty=Difficulty(document["difficulty"]),
        estimate_minutes=document["estimate_minutes"],
        status=ContentStatus(document["status"]),
        order=document.get("order", DEFAULT_CURRICULUM_ORDER),
        references=ItemReferences(
            study_guides=tuple(references.get("study_guides", ())),
            links=tuple(references.get("links", ())),
        ),
        related=tuple(document.get("related", ())),
    )


def _check_location(directory: Path, meta: ItemMeta, source: str) -> None:
    """I2: the directory is the slug and sits in the directory of its track."""
    issues: list[ContentIssue] = []
    if directory.name != meta.slug:
        message = f"directory {directory.name} does not match slug {meta.slug}"
        issues.append(ContentIssue(source, "slug", message))
    track_directory = directory.parent.name
    if track_directory != meta.track:
        message = f"item is in {TRACKS_DIRECTORY}/{track_directory} but its track is {meta.track}"
        issues.append(ContentIssue(source, "track", message))
    if issues:
        raise ContentError(issues)
