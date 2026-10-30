"""Loads autograded problems from problems/<id>-<slug>/ (docs/specs/problem-format.md).

The conformance suite uses the same format under runners/conformance/ (docs/specs/runners.md).
"""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from coding_study.adapters.document_index import DocumentIndex, file_stamp, index_key
from coding_study.adapters.problem_documents import cases_from_document, meta_from_document
from coding_study.adapters.schema_validation import (
    META_SCHEMA_FILE,
    SCHEMAS_DIRECTORY,
    TESTS_SCHEMA_FILE,
    SchemaValidator,
)
from coding_study.domain.errors import ContentError, ContentIssue, UnknownProblemError
from coding_study.domain.layout import language_of_extension
from coding_study.domain.problem import Language, Problem, ProblemMeta, ProblemSummary

PROBLEMS_DIRECTORY = "problems"
META_FILE = "meta.yaml"
TESTS_FILE = "tests.json"
SOLUTIONS_DIRECTORY = "solutions"
ID_DIGITS = 4

type _Parser = Callable[[str, str], Any]

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
"""The libyaml loader when PyYAML was built with it: the same documents, several times faster."""


class FsProblemRepository:
    def __init__(
        self,
        root: Path,
        problems_directory: str = PROBLEMS_DIRECTORY,
        index: DocumentIndex | None = None,
    ) -> None:
        self._root = root
        self._problems = root / problems_directory
        self._index = index
        self._workspace = False
        schemas = root / SCHEMAS_DIRECTORY
        self._meta_schema_stamp = file_stamp(schemas / META_SCHEMA_FILE)
        self._meta_schema = SchemaValidator.from_file(schemas / META_SCHEMA_FILE)
        self._tests_schema = SchemaValidator.from_file(schemas / TESTS_SCHEMA_FILE)

    def over(self, root: Path) -> "FsProblemRepository":
        """These schemas and this index over `root`'s problems/ (a workspace's own problems)."""
        repository = copy.copy(self)
        repository._workspace = True
        repository._root = root
        repository._problems = root / PROBLEMS_DIRECTORY
        return repository

    def slugs(self) -> tuple[str, ...]:
        """The slug of every `<id>-<slug>` directory, valid or not, in directory order."""
        return tuple(_slug_of(directory.name) or "" for directory in self._problem_directories())

    def load(self, slug: str) -> Problem:
        directory = self._directory_of(slug)
        meta_file, tests_file = directory / META_FILE, directory / TESTS_FILE
        meta_document, meta_issues = self._validated(meta_file, parse_yaml, self._meta_schema)
        tests_document, tests_issues = self._validated(tests_file, _parse_json, self._tests_schema)
        if meta_issues or tests_issues:
            raise ContentError([*meta_issues, *tests_issues])
        meta = self._meta(directory, meta_document)
        cases = cases_from_document(tests_document, meta.comparator, self._source(tests_file))
        return Problem(meta, cases)

    def list_summaries(self) -> tuple[ProblemSummary, ...]:
        summaries: list[ProblemSummary] = []
        issues: list[ContentIssue] = []
        directories = self._problem_directories()
        for directory in directories:
            try:
                summaries.append(self._summary(directory))
            except ContentError as error:
                issues.extend(error.issues)
        self._save_index(directories)
        if issues:
            raise ContentError(issues)
        return tuple(summaries)

    def _summary(self, directory: Path) -> ProblemSummary:
        meta_file = directory / META_FILE
        meta_document, issues = self._indexed_meta(meta_file)
        if issues:
            raise ContentError(issues)
        meta = self._meta(directory, meta_document)
        return ProblemSummary(meta, self._source(directory), _reference_languages(directory, meta))

    def _indexed_meta(self, meta_file: Path) -> tuple[Any, list[ContentIssue]]:
        def read() -> tuple[Any, list[ContentIssue]]:
            return self._validated(meta_file, parse_yaml, self._meta_schema)

        if self._index is None:
            return read()
        return self._index.validated(index_key(meta_file), meta_file, self._meta_schema_stamp, read)

    def _save_index(self, directories: list[Path]) -> None:
        if self._index is None:
            return
        listed = {index_key(directory / META_FILE) for directory in directories}
        self._index.retain(f"{index_key(self._problems)}/", listed)
        self._index.save()

    def _meta(self, directory: Path, meta_document: Any) -> ProblemMeta:
        source = self._source(directory / META_FILE)
        meta = meta_from_document(meta_document, source, self._workspace)
        self._check_directory_name(directory, meta)
        return meta

    def _directory_of(self, slug: str) -> Path:
        for directory in self._problem_directories():
            if _slug_of(directory.name) == slug:
                return directory
        raise UnknownProblemError(slug)

    def _problem_directories(self) -> list[Path]:
        if not self._problems.is_dir():
            return []
        return [
            directory
            for directory in sorted(self._problems.iterdir())
            if directory.is_dir() and _slug_of(directory.name) is not None
        ]

    def _validated(
        self, path: Path, parse: _Parser, schema: SchemaValidator
    ) -> tuple[Any, list[ContentIssue]]:
        source = self._source(path)
        try:
            document = parse(read_content_file(path, source), source)
        except ContentError as error:
            return None, list(error.issues)
        return document, schema.violations(document, source)

    def _check_directory_name(self, directory: Path, meta: ProblemMeta) -> None:
        if directory.name != meta.directory_name:
            message = (
                f"directory name {directory.name} does not match id and slug "
                f"(expected {meta.directory_name})"
            )
            raise ContentError([ContentIssue(self._source(directory / META_FILE), "id", message)])

    def _source(self, path: Path) -> str:
        return path.relative_to(self._root).as_posix()


def _slug_of(directory_name: str) -> str | None:
    """The slug of an `<id>-<slug>` directory name, or None for any other name."""
    prefix, separator, slug = directory_name.partition("-")
    if separator and len(prefix) == ID_DIGITS and prefix.isdigit():
        return slug
    return None


def _reference_languages(directory: Path, meta: ProblemMeta) -> tuple[Language, ...]:
    solutions = directory / SOLUTIONS_DIRECTORY
    if not solutions.is_dir():
        return ()
    approach_ids = {approach.id for approach in meta.approaches}
    found = {
        language_of_extension(path.suffix.removeprefix("."))
        for path in solutions.iterdir()
        if path.is_file() and path.stem in approach_ids
    }
    return tuple(language for language in Language if language in found)


def read_content_file(path: Path, source: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ContentError([ContentIssue(source, "", "file not found")]) from None


def parse_yaml(text: str, source: str) -> Any:
    try:
        return yaml.load(text, Loader=_YAML_LOADER)
    except yaml.MarkedYAMLError as error:
        mark = error.problem_mark
        location = f"line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        raise ContentError([ContentIssue(source, location, error.problem or str(error))]) from None
    except yaml.YAMLError as error:
        raise ContentError([ContentIssue(source, "", str(error))]) from None


def _parse_json(text: str, source: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        location = f"line {error.lineno}, column {error.colno}"
        raise ContentError([ContentIssue(source, location, error.msg)]) from None
