"""`cstudy verify` checks on non-autograded items (docs/specs/authoring.md#items).

The schema and the directory rules (I1, I2) fail while loading `item.yaml`; slug uniqueness needs
every problem and item and is checked by the caller. This module checks the Markdown files and
the change under review (I3 to I7) and what `status: ready` adds.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from coding_study.domain.errors import ContentIssue
from coding_study.domain.items import (
    CHANGE_DIRECTORY,
    CHANGE_FILE,
    NOTES_TITLE_SUFFIX,
    PROMPT_FILE,
    REFERENCE_FILE,
    REFERENCE_TITLE_SUFFIX,
    TEMPLATE_FILE,
    ItemMeta,
)
from coding_study.domain.markdown import MarkdownDocument
from coding_study.domain.problem import ContentStatus, Track
from coding_study.domain.problem_files import RUBRIC_FILE
from coding_study.domain.rubric import RUBRIC_TITLE_SUFFIX, item_rubric_issues
from coding_study.domain.static_checks import PLACEHOLDER

PROMPT_SECTIONS: dict[Track, tuple[str, ...]] = {
    Track.SYSTEM_DESIGN: (
        "Question",
        "Functional requirements",
        "Non-functional requirements",
        "Scale",
    ),
    Track.CODE_REVIEW: ("Context", "Task"),
}
SYSTEM_DESIGN_REFERENCE_SECTIONS = (
    "Requirements",
    "Estimates",
    "API",
    "Data model",
    "High-level design",
    "Deep dives",
    "Trade-offs",
)
SEVERITIES = ("Blocker", "Major", "Minor", "Nit")
"""Code review reference sections, most severe first."""
_ISSUE = re.compile(r"\s*- \S")


@dataclass(frozen=True, slots=True)
class ItemContent:
    """Everything the item checks read, gathered from one item directory."""

    directory: str
    """Repository-relative, e.g. `tracks/system-design/url-shortener`."""
    meta: ItemMeta
    prompt: str | None
    rubric: str | None
    reference: str | None
    template: str | None
    change: str | None = None
    """change.diff, or None when the file does not exist."""
    change_files: tuple[str, ...] = ()
    """File names in `files/`."""


def item_static_checks(content: ItemContent) -> tuple[ContentIssue, ...]:
    issues = _Issues(content.directory)
    title = content.meta.title
    prompt = issues.document(PROMPT_FILE, content.prompt, title)
    if prompt is not None:
        _required_sections(issues.at(PROMPT_FILE), prompt, PROMPT_SECTIONS[content.meta.track])
        _placeholders(issues.at(PROMPT_FILE), prompt)
    if content.rubric is None:
        issues.error(RUBRIC_FILE, "missing")
    else:
        for issue in item_rubric_issues(content.rubric, title + RUBRIC_TITLE_SUFFIX):
            issues.error(RUBRIC_FILE, issue)
        _placeholders(issues.at(RUBRIC_FILE), MarkdownDocument(content.rubric))
    reference = issues.document(REFERENCE_FILE, content.reference, title + REFERENCE_TITLE_SUFFIX)
    if reference is not None:
        _reference(issues.at(REFERENCE_FILE), reference, content.meta.track)
        _placeholders(issues.at(REFERENCE_FILE), reference)
    template = issues.document(TEMPLATE_FILE, content.template, title + NOTES_TITLE_SUFFIX)
    if template is not None and not template.sections(2):
        issues.error(TEMPLATE_FILE, 'needs at least one "## " section')
    _change(issues, content)
    return tuple(issues.errors)


def item_ready_problems(content: ItemContent) -> tuple[str, ...]:
    """Every reason the item is not ready; empty when it is."""
    meta = content.meta
    problems: list[str] = []
    if meta.status is not ContentStatus.READY:
        problems.append(f"status is {meta.status}, not ready")
    references = meta.references
    if meta.track is Track.SYSTEM_DESIGN and not (references.links or references.study_guides):
        problems.append("system-design items need at least one reference (links or study_guides)")
    return tuple(problems)


class _FileIssues:
    def __init__(self, issues: "_Issues", name: str) -> None:
        self._issues = issues
        self._name = name

    def error(self, message: str) -> None:
        self._issues.error(self._name, message)


class _Issues:
    def __init__(self, directory: str) -> None:
        self._directory = directory
        self.errors: list[ContentIssue] = []

    def error(self, name: str, message: str) -> None:
        source = f"{self._directory}/{name}" if name else self._directory
        self.errors.append(ContentIssue(source, "", message))

    def at(self, name: str) -> _FileIssues:
        return _FileIssues(self, name)

    def document(self, name: str, text: str | None, title: str) -> MarkdownDocument | None:
        """The parsed file, after reporting a missing file or a wrong `# <title>`."""
        if text is None:
            self.error(name, "missing")
            return None
        document = MarkdownDocument(text)
        if document.title != title:
            self.error(name, f'title "{document.title}" must be "{title}"')
        return document


def _required_sections(
    issues: _FileIssues, document: MarkdownDocument, titles: Sequence[str]
) -> None:
    sections = {section.title: section for section in document.sections(2)}
    for title in titles:
        section = sections.get(title)
        if section is None:
            issues.error(f'missing "## {title}"')
        elif not section.text:
            issues.error(f'"## {title}" is empty')
    _order(issues, [title for title in sections if title in titles], titles)


def _order(issues: _FileIssues, found: Sequence[str], expected: Sequence[str]) -> None:
    for position, title in enumerate(found):
        rank = expected.index(title)
        later = next((other for other in found[:position] if expected.index(other) > rank), None)
        if later is not None:
            issues.error(f'"## {title}" must come before "## {later}"')


def _reference(issues: _FileIssues, document: MarkdownDocument, track: Track) -> None:
    if track is Track.SYSTEM_DESIGN:
        _required_sections(issues, document, SYSTEM_DESIGN_REFERENCE_SECTIONS)
        return
    sections = document.sections(2)
    if not sections:
        issues.error(f"needs at least one severity section: {', '.join(SEVERITIES)}")
    for section in sections:
        if section.title not in SEVERITIES:
            issues.error(f'"## {section.title}" is not a severity: {", ".join(SEVERITIES)}')
        elif not any(_ISSUE.match(line) for line in section.body):
            issues.error(f'"## {section.title}" lists no "- " issue')
    severities = [section.title for section in sections if section.title in SEVERITIES]
    _order(issues, severities, SEVERITIES)


def _placeholders(issues: _FileIssues, document: MarkdownDocument) -> None:
    for section in document.sections(2):
        if PLACEHOLDER in section.text:
            issues.error(f'"## {section.title}" contains {PLACEHOLDER}')


def _change(issues: _Issues, content: ItemContent) -> None:
    """I7: code review items carry exactly one form of the change; other items carry none."""
    has_diff = content.change is not None
    has_files = bool(content.change_files)
    if content.meta.track is not Track.CODE_REVIEW:
        if has_diff:
            issues.error(CHANGE_FILE, "only code-review items have a change under review")
        if has_files:
            issues.error(CHANGE_DIRECTORY, "only code-review items have a change under review")
        return
    if has_diff == has_files:
        issues.error("", f"needs {CHANGE_FILE} or {CHANGE_DIRECTORY}/ (exactly one)")
    elif content.change is not None and not content.change.strip():
        issues.error(CHANGE_FILE, "is empty")
