"""The user docs in user-docs/ (docs/specs/user-docs.md): one Markdown page per topic, each with
YAML front matter that `schemas/user-doc.schema.json` validates (D1).

Every `*.md` directly inside `user-docs/` is a page; hidden entries and `__pycache__` are left
out, as a checkout may hold them. The schema loads on first use, so a content root without docs
never reads it.
"""

from pathlib import Path

from coding_study.adapters.fs_problem_repository import parse_yaml, read_content_file
from coding_study.adapters.schema_validation import SCHEMAS_DIRECTORY, SchemaValidator
from coding_study.domain.doc_checks import page_file
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.user_docs import (
    DOCS_DIRECTORY,
    PAGE_SUFFIX,
    DocPage,
    split_front_matter,
)

DOC_SCHEMA_FILE = "user-doc.schema.json"
NO_FRONT_MATTER = "starts with front matter between --- lines"
FOLDER_MARK = "/"
_SKIPPED_NAMES = ("__pycache__",)
_HIDDEN_PREFIX = "."


class FsUserDocs:
    """`UserDocs` for the user-docs/ directory under a content root."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._folder = root / DOCS_DIRECTORY
        self._validator: SchemaValidator | None = None

    def slugs(self) -> tuple[str, ...]:
        return tuple(
            entry.name.removesuffix(PAGE_SUFFIX)
            for entry in self._visible()
            if entry.is_file() and entry.name.endswith(PAGE_SUFFIX)
        )

    def entries(self) -> tuple[str, ...]:
        return tuple(
            f"{entry.name}{FOLDER_MARK}" if entry.is_dir() else entry.name
            for entry in self._visible()
        )

    def load(self, slug: str) -> DocPage:
        source = page_file(slug)
        text = read_content_file(self._folder / f"{slug}{PAGE_SUFFIX}", source)
        parts = split_front_matter(text)
        if parts is None:
            raise ContentError([ContentIssue(source, "", NO_FRONT_MATTER)])
        front, markdown, first_line = parts
        # The newline puts the YAML's line numbers on the file's: its first line is `---`.
        document = parse_yaml(f"\n{front}", source)
        issues = self._schema().violations(document, source)
        if issues:
            raise ContentError(issues)
        return DocPage(
            slug=slug,
            title=document["title"],
            summary=document["summary"],
            section=document["section"],
            order=document["order"],
            markdown=markdown,
            first_line=first_line,
        )

    def _schema(self) -> SchemaValidator:
        if self._validator is None:
            path = self._root / SCHEMAS_DIRECTORY / DOC_SCHEMA_FILE
            self._validator = SchemaValidator.from_file(path)
        return self._validator

    def _visible(self) -> list[Path]:
        if not self._folder.is_dir():
            return []
        return [
            entry
            for entry in sorted(self._folder.iterdir())
            if not entry.name.startswith(_HIDDEN_PREFIX) and entry.name not in _SKIPPED_NAMES
        ]
