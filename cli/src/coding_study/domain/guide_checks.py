"""The static checks of concept guides (G2 to G9) and learning paths (P1 to P5), as
docs/specs/guides.md#static-checks lists them. G1, the schema of `meta.yaml`, is the adapter's.
"""

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from coding_study.domain.concept_guides import (
    EXAMPLES_DIRECTORY,
    GUIDE_FILE,
    GUIDE_META_FILE,
    PATHS_DIRECTORY,
    GuideMeta,
    LearningPath,
    StepKind,
    is_slug,
)
from coding_study.domain.errors import ContentIssue
from coding_study.domain.guide_markdown import Fence, GuideMarkdown, mermaid_digest
from coding_study.domain.markdown import MarkdownDocument

GUIDE_SECTIONS = (
    "The idea",
    "A worked example",
    "When to use it",
    "Common traps",
    "Complexity",
    "Expert notes",
    "Practice",
    "Further reading",
)
PRACTICE = "Practice"
FURTHER_READING = "Further reading"
PLACEHOLDER = "TODO"
LINK = "https://"
EXAMPLE_LANGUAGES = {
    ".go": "go",
    ".java": "java",
    ".js": "javascript",
    ".mjs": "javascript",
    ".py": "python",
}
"""What an example may be written in, by extension, and the language its fence names."""
DIAGRAM_TYPES = re.compile(
    r"(?:(?:flowchart|graph)[ \t]+(?:TD|TB|BT|LR|RL)"
    r"|sequenceDiagram|stateDiagram|stateDiagram-v2|classDiagram|erDiagram)[ \t]*"
)
"""The Mermaid types the text renderer of tools/guides/ draws."""
_ACCESSIBLE_TITLE = re.compile(r"\s*accTitle\s*:\s*\S.*")
_ACCESSIBLE_DESCRIPTION = re.compile(r"\s*accDescr\s*(?::\s*\S.*|\{.*)")
MAX_DRAWING_WIDTH = 100
REDRAW = "run pnpm render in tools/guides/"


@dataclass(frozen=True, slots=True)
class GuideContent:
    directory: str
    """Repository-relative, e.g. `guides/hash-functions`."""
    meta: GuideMeta
    markdown: str | None
    """guide.md; None when it is missing."""
    files: tuple[str, ...]
    """Every file under the folder, relative to it, such as `examples/buckets.py`."""
    examples: Mapping[str, str]
    """The text of each file under `examples/`, by its relative path."""


@dataclass(frozen=True, slots=True)
class CatalogFacts:
    guides: Mapping[str, GuideMeta]
    """Every guide that loaded, by slug."""
    problems: Mapping[str, int]
    """Every problem slug, with its number of levels (0 for a problem without levels)."""


def guide_static_checks(content: GuideContent, catalog: CatalogFacts) -> tuple[ContentIssue, ...]:
    issues = _Issues(content.directory)
    _folder(issues, content)
    _links(issues, content.meta, catalog)
    _cycle(issues, content.meta, catalog.guides)
    if content.markdown is None:
        issues.add(GUIDE_FILE, "missing")
    else:
        _GuideFile(issues, content, catalog).check(content.markdown)
    return tuple(issues.found)


def path_static_checks(
    file: str, path: LearningPath, catalog: CatalogFacts
) -> tuple[ContentIssue, ...]:
    """P1's file name and P2 to P5; `file` is repository-relative."""
    found: list[ContentIssue] = []
    if not is_slug(path.slug):
        found.append(ContentIssue(file, "", "the name must be a kebab-case slug, such as hashing"))
    seen: dict[tuple[StepKind, str, int | None], int] = {}
    for position, step in enumerate(path.steps):
        location = f"steps[{position}]"
        for message in _step_issues(path, position, catalog):
            found.append(ContentIssue(file, location, message))
        key = (step.kind, step.slug, step.level)
        if key in seen:
            found.append(ContentIssue(file, location, f"the same step as steps[{seen[key]}]"))
        seen.setdefault(key, position)
    return tuple(found)


def _step_issues(path: LearningPath, position: int, catalog: CatalogFacts) -> Iterator[str]:
    step = path.steps[position]
    if step.kind is StepKind.GUIDE:
        guide = catalog.guides.get(step.slug)
        if guide is None:
            yield f'"{step.slug}" is not a guide'
            return
        earlier = {other.slug for other in path.steps[:position] if other.kind is StepKind.GUIDE}
        for prerequisite in guide.prerequisites:
            if prerequisite not in earlier:
                yield f"{step.slug} needs {prerequisite} as an earlier step"
        return
    levels = catalog.problems.get(step.slug)
    if levels is None:
        yield f'"{step.slug}" is not a problem'
    elif step.level is not None and levels == 0:
        yield f"{step.slug} has no levels; a level fits a progressive or project problem"
    elif step.level is not None and step.level > levels:
        yield f"{step.slug} has {levels} levels, not {step.level}"


class _Issues:
    def __init__(self, directory: str) -> None:
        self._directory = directory
        self.found: list[ContentIssue] = []

    def add(self, name: str, message: str, location: str = "") -> None:
        file = f"{self._directory}/{name}" if name else self._directory
        self.found.append(ContentIssue(file, location, message))


def _folder(issues: _Issues, content: GuideContent) -> None:
    """G2"""
    if content.meta.slug == PATHS_DIRECTORY:
        issues.add("", f'"{PATHS_DIRECTORY}" is reserved for the paths folder')
    elif not is_slug(content.meta.slug):
        issues.add("", "the folder's name must be a kebab-case slug, such as hash-functions")
    for name in content.files:
        if not _belongs(name):
            issues.add(
                "",
                f'"{name}" does not belong in a guide: '
                f"a guide holds {GUIDE_META_FILE}, {GUIDE_FILE} and {EXAMPLES_DIRECTORY}/",
            )


def _belongs(name: str) -> bool:
    parts = name.split("/")
    if len(parts) == 1:
        return name in (GUIDE_META_FILE, GUIDE_FILE)
    return len(parts) == 2 and parts[0] == EXAMPLES_DIRECTORY


def _links(issues: _Issues, meta: GuideMeta, catalog: CatalogFacts) -> None:
    """G4, in meta.yaml"""
    for field, slugs in (("prerequisites", meta.prerequisites), ("related", meta.related)):
        for slug in slugs:
            if slug == meta.slug:
                issues.add(GUIDE_META_FILE, "a guide does not link to itself", field)
            elif slug not in catalog.guides:
                issues.add(GUIDE_META_FILE, f'"{slug}" is not a guide', field)
    for slug in meta.problems:
        if slug not in catalog.problems:
            issues.add(GUIDE_META_FILE, f'"{slug}" is not a problem', "problems")


def _cycle(issues: _Issues, meta: GuideMeta, guides: Mapping[str, GuideMeta]) -> None:
    """G5: a chain of prerequisites that leads back to this guide."""
    cycle = _path_back(meta.slug, meta.slug, guides, ())
    if cycle:
        chain = " -> ".join((meta.slug, *cycle))
        issues.add(GUIDE_META_FILE, f"they form a cycle: {chain}", "prerequisites")


def _path_back(
    target: str, current: str, guides: Mapping[str, GuideMeta], seen: tuple[str, ...]
) -> tuple[str, ...]:
    found = guides.get(current)
    for prerequisite in found.prerequisites if found else ():
        if prerequisite == target:
            return (*seen, prerequisite)
        if prerequisite in seen:
            continue
        cycle = _path_back(target, prerequisite, guides, (*seen, prerequisite))
        if cycle:
            return cycle
    return ()


class _GuideFile:
    def __init__(self, issues: _Issues, content: GuideContent, catalog: CatalogFacts) -> None:
        self._issues = issues
        self._content = content
        self._catalog = catalog

    def check(self, text: str) -> None:
        document = MarkdownDocument(text)
        self._structure(document, text)
        markdown = GuideMarkdown(text)
        self._examples(markdown)
        self._diagrams(markdown)

    def error(self, message: str, line: int | None = None) -> None:
        location = f"line {line + 1}" if line is not None else ""
        self._issues.add(GUIDE_FILE, message, location)

    def _structure(self, document: MarkdownDocument, text: str) -> None:
        """G3, G4's Practice and G9"""
        title = self._content.meta.title
        if document.title != title:
            self.error(f'title "{document.title}" must be "{title}"')
        sections = {section.title: section for section in document.sections(2)}
        for name in GUIDE_SECTIONS:
            section = sections.get(name)
            if section is None:
                self.error(f'missing "## {name}"')
            elif not section.text:
                self.error(f'"## {name}" is empty')
        self._order([name for name in sections if name in GUIDE_SECTIONS])
        if PLACEHOLDER in text:
            self.error(f"contains {PLACEHOLDER}")
        practice = sections.get(PRACTICE)
        for slug in self._content.meta.problems if practice else ():
            if practice is not None and not _names(practice.text, slug):
                self.error(f'"## {PRACTICE}" does not name problem "{slug}"')
        reading = sections.get(FURTHER_READING)
        if reading is not None and reading.text and LINK not in reading.text:
            self.error(f'"## {FURTHER_READING}" has no {LINK} link')

    def _order(self, found: Sequence[str]) -> None:
        for position, name in enumerate(found):
            rank = GUIDE_SECTIONS.index(name)
            later = next(
                (other for other in found[:position] if GUIDE_SECTIONS.index(other) > rank), None
            )
            if later is not None:
                self.error(f'"## {name}" must come before "## {later}"')

    def _examples(self, markdown: GuideMarkdown) -> None:
        """G6"""
        examples = self._content.examples
        embedded: dict[str, int] = {}
        for fence in markdown.example_fences():
            name = fence.argument or ""
            embedded[name] = embedded.get(name, 0) + 1
            self._example(fence, name)
        for name in sorted(examples):
            count = embedded.get(name, 0)
            if count == 0:
                self.error(f"{name} is never embedded")
            elif count > 1:
                self.error(f"{name} is embedded {count} times; embed it once")
        outputs: dict[str, int] = {}
        for fence in markdown.output_fences():
            name = fence.argument or ""
            outputs[name] = outputs.get(name, 0) + 1
            if name not in embedded:
                self.error(f"output of {name}, which is not embedded", fence.start)
        for name in embedded:
            count = outputs.get(name, 0)
            if count != 1 and name in examples:
                self.error(f"{name} needs one output block, not {count}")

    def _example(self, fence: Fence, name: str) -> None:
        text = self._content.examples.get(name)
        suffix = _suffix(name)
        language = EXAMPLE_LANGUAGES.get(suffix)
        if language is None:
            supported = ", ".join(sorted(EXAMPLE_LANGUAGES))
            supported = " or ".join(supported.rsplit(", ", 1))
            self.error(f"{name}: an example is {supported}", fence.start)
        elif text is None:
            self.error(f"{name} does not exist", fence.start)
        elif fence.language != language:
            self.error(f'{name} is embedded as "{fence.language}"; use "{language}"', fence.start)
        elif fence.content != text:
            self.error(f"the copy of {name} differs from the file", fence.start)

    def _diagrams(self, markdown: GuideMarkdown) -> None:
        """G7 and G8"""
        for diagram in markdown.mermaid_fences():
            for message in _diagram_issues(diagram):
                self.error(f"the diagram {message}", diagram.start)
            drawing = markdown.text_drawing(diagram)
            if drawing is None:
                self.error(f"the diagram has no text drawing: {REDRAW}", diagram.start)
                continue
            if drawing.digest != mermaid_digest(diagram.content):
                self.error(f"the text drawing is stale: {REDRAW}", diagram.start)
            for offset, line in enumerate(drawing.fence.lines, start=1):
                if len(line) > MAX_DRAWING_WIDTH:
                    self.error(
                        f"the text drawing is {len(line)} characters wide; "
                        f"at most {MAX_DRAWING_WIDTH} fit: simplify the diagram",
                        drawing.fence.start + offset,
                    )
        for line in markdown.stray_markers():
            self.error("a text-drawing marker with no diagram before it", line)


def _diagram_issues(diagram: Fence) -> Iterator[str]:
    first = next((line.strip() for line in diagram.lines if line.strip()), "")
    if DIAGRAM_TYPES.fullmatch(first) is None:
        yield f'starts with "{first}", which is not a type'
    if not any(_ACCESSIBLE_TITLE.fullmatch(line) for line in diagram.lines):
        yield "has no accTitle line"
    if not any(_ACCESSIBLE_DESCRIPTION.fullmatch(line) for line in diagram.lines):
        yield "has no accDescr line"


def _names(text: str, slug: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(slug)}(?![\w-])", text) is not None


def _suffix(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    return f".{base.rsplit('.', 1)[1]}" if "." in base else ""
