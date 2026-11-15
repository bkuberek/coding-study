"""Loads rubric-checked problems from problems/<slug>/ (docs/specs/compatibility.md).

A directory of `problems/` whose `kind` is a rubric kind is a rubric problem here; any other
directory belongs to `FsProblemRepository` and is absent here.
"""

from pathlib import Path
from typing import Any

from coding_study.adapters.document_index import DocumentIndex, file_stamp, index_key
from coding_study.adapters.fs_problem_repository import (
    META_FILE,
    PROBLEMS_DIRECTORY,
    is_rubric_document,
    parse_yaml,
    read_content_file,
    slug_directories,
)
from coding_study.adapters.problem_documents import labels_from_document
from coding_study.adapters.schema_validation import (
    META_SCHEMA_FILE,
    SCHEMAS_DIRECTORY,
    SchemaValidator,
)
from coding_study.domain.errors import ContentError, ContentIssue, UnknownProblemError
from coding_study.domain.items import ItemMeta, ItemReferences
from coding_study.domain.problem import (
    DEFAULT_CURRICULUM_ORDER,
    SLUG_PATTERN,
    ContentStatus,
    Difficulty,
    Track,
)


class FsItemRepository:
    """`ItemRepository` for the rubric problems of the problems/ directory under the content
    root."""

    def __init__(self, root: Path, index: DocumentIndex | None = None) -> None:
        self._root = root
        self._problems = root / PROBLEMS_DIRECTORY
        self._index = index
        schema_file = root / SCHEMAS_DIRECTORY / META_SCHEMA_FILE
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
        directories = slug_directories(self._problems)
        for directory in directories:
            document, found = self._validated(directory / META_FILE)
            if not is_rubric_document(document):
                continue
            try:
                items.append(self._item(directory, document, found))
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
        document, issues = self._validated(directory / META_FILE)
        return self._item(directory, document, issues)

    def _item(self, directory: Path, document: Any, issues: list[ContentIssue]) -> ItemMeta:
        if issues:
            raise ContentError(issues)
        meta = _item_meta(document)
        _check_directory_name(directory, meta, self._source(directory / META_FILE))
        return meta

    def _validated(self, path: Path) -> tuple[Any, list[ContentIssue]]:
        source = self._source(path)

        def read() -> tuple[Any, list[ContentIssue]]:
            try:
                document = parse_yaml(read_content_file(path, source), source)
            except ContentError as error:
                return None, list(error.issues)
            return document, self._schema.violations(document, source)

        if self._index is None:
            return read()
        return self._index.validated(index_key(path), path, self._schema_stamp, read)

    def _save_index(self, directories: list[Path]) -> None:
        if self._index is None:
            return
        listed = {index_key(directory / META_FILE) for directory in directories}
        self._index.retain(f"{index_key(self._problems)}/", listed)
        self._index.save()

    def _directory_of(self, slug: str) -> Path:
        directory = self._problems / slug
        if (
            SLUG_PATTERN.fullmatch(slug)
            and directory.is_dir()
            and is_rubric_document(self._validated(directory / META_FILE)[0])
        ):
            return directory
        raise UnknownProblemError(slug)

    def _item_directories(self) -> list[Path]:
        """The rubric problems in name order."""
        return [
            directory
            for directory in slug_directories(self._problems)
            if is_rubric_document(self._validated(directory / META_FILE)[0])
        ]

    def _source(self, path: Path) -> str:
        return path.relative_to(self._root).as_posix()


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
        labels=labels_from_document(document),
        references=ItemReferences(
            study_guides=tuple(references.get("study_guides", ())),
            links=tuple(references.get("links", ())),
        ),
        related=tuple(document.get("related", ())),
    )


def _check_directory_name(directory: Path, meta: ItemMeta, source: str) -> None:
    """I2: the directory is named by the slug."""
    if directory.name != meta.slug:
        message = f"directory name {directory.name} does not match slug {meta.slug}"
        raise ContentError([ContentIssue(source, "slug", message)])
