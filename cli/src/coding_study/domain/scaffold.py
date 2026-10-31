"""What `cstudy new` writes (docs/specs/cli.md#cstudy-new): a draft problem from one of 8 templates.

Template files hold `{{name}}` placeholders (`Scaffold.placeholders`); everything else in them
is literal, including the `TODO` text that `cstudy verify --static` rejects in problem.md until
the author replaces it.
"""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Difficulty, Track
from coding_study.domain.problem_files import RUBRIC_FILE
from coding_study.domain.rubric import LLD_RUBRIC_SECTIONS, rubric_skeleton
from coding_study.domain.taxonomy import PATTERNS

ID_DIGITS = 4
WORKSPACE_FIRST_ID = 5001
"""The first id of a problem `cstudy new` writes into a workspace, above any catalog id."""
SLUG_PATTERN = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
DEFAULT_DIFFICULTY = Difficulty.MEDIUM
PROBLEM_TRACKS = (Track.DSA, Track.PRACTICAL, Track.LLD, Track.CONCURRENCY, Track.DEBUGGING)
"""Autograded tracks, whose content lives in problems/ (docs/specs/content.md#tracks)."""
_PLACEHOLDER = re.compile(r"\{\{(?P<name>[a-z_]+)\}\}")


class TemplateName(StrEnum):
    ARRAY = "array"
    TREE = "tree"
    DESIGN = "design"
    PROGRESSIVE = "progressive"
    CONCURRENT = "concurrent"
    PROJECT_PYTHON = "project-python"
    """A project problem in Python: a starter folder and the reference's overlay on it."""
    PROJECT_TYPESCRIPT = "project-typescript"
    """A project problem in TypeScript: a starter folder and the reference's overlay on it."""
    PROJECT_GO = "project-go"
    """A project problem in Go: a starter module and the reference's overlay on it."""


@dataclass(frozen=True, slots=True)
class TemplateDefaults:
    track: Track
    pattern: str | None


TEMPLATE_DEFAULTS: Mapping[TemplateName, TemplateDefaults] = {
    TemplateName.ARRAY: TemplateDefaults(Track.DSA, "arrays-hashing"),
    TemplateName.TREE: TemplateDefaults(Track.DSA, "trees"),
    TemplateName.DESIGN: TemplateDefaults(Track.DSA, "arrays-hashing"),
    TemplateName.PROGRESSIVE: TemplateDefaults(Track.PRACTICAL, None),
    TemplateName.CONCURRENT: TemplateDefaults(Track.CONCURRENCY, None),
    TemplateName.PROJECT_PYTHON: TemplateDefaults(Track.PRACTICAL, None),
    TemplateName.PROJECT_TYPESCRIPT: TemplateDefaults(Track.PRACTICAL, None),
    TemplateName.PROJECT_GO: TemplateDefaults(Track.PRACTICAL, None),
}


@dataclass(frozen=True, slots=True)
class ScaffoldRequest:
    slug: str
    template: TemplateName = TemplateName.ARRAY
    track: Track | None = None
    """None: the template's track."""
    title: str | None = None
    """None: from the slug, `two-sum` becomes `Two Sum`."""
    difficulty: Difficulty | None = None
    pattern: str | None = None
    """The primary pattern; None: the template's pattern, if any."""


@dataclass(frozen=True, slots=True)
class Scaffold:
    id: str
    slug: str
    title: str
    difficulty: Difficulty
    track: Track
    patterns: tuple[str, ...]

    @property
    def directory_name(self) -> str:
        return f"{self.id}-{self.slug}"

    def placeholders(self) -> Mapping[str, str]:
        words = self.slug.split("-")
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "title_yaml": json.dumps(self.title),
            "difficulty": self.difficulty.value,
            "track": self.track.value,
            "patterns": f"patterns: [{', '.join(self.patterns)}]" if self.patterns else "",
            "function_name": words[0] + "".join(word.capitalize() for word in words[1:]),
            "class_name": "".join(word.capitalize() for word in words),
        }

    def track_files(self) -> Mapping[str, str]:
        """Files the track needs beyond the template's: `rubric.md` for `lld` (check S8)."""
        if self.track is Track.LLD:
            return {RUBRIC_FILE: rubric_skeleton(self.title, LLD_RUBRIC_SECTIONS)}
        return {}


def plan_scaffold(request: ScaffoldRequest, problem_id: str) -> Scaffold:
    """Raises UsageError for an invalid slug, title, track or pattern."""
    if not SLUG_PATTERN.fullmatch(request.slug):
        raise UsageError(
            f'invalid slug "{request.slug}": use lowercase words joined by "-", e.g. two-sum'
        )
    defaults = TEMPLATE_DEFAULTS[request.template]
    track = request.track or defaults.track
    if track not in PROBLEM_TRACKS:
        names = ", ".join(PROBLEM_TRACKS)
        raise UsageError(f"cstudy new scaffolds autograded problems; use a track from {names}")
    return Scaffold(
        id=problem_id,
        slug=request.slug,
        title=_title(request),
        difficulty=request.difficulty or DEFAULT_DIFFICULTY,
        track=track,
        patterns=_patterns(request.pattern or defaults.pattern, track),
    )


def next_problem_id(directory_names: Sequence[str], first_id: int = 1) -> str:
    """The highest `<id>-` prefix plus one, zero-padded, and at least `first_id`."""
    ids = [
        int(prefix)
        for name in directory_names
        if (prefix := name.partition("-")[0]).isdigit() and len(prefix) == ID_DIGITS
    ]
    return f"{max(max(ids, default=0) + 1, first_id):0{ID_DIGITS}d}"


def render_template(text: str, placeholders: Mapping[str, str]) -> str:
    """Replaces every `{{name}}`; a line holding only a placeholder that renders empty is
    dropped. Raises KeyError for an unknown placeholder."""
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        rendered = _PLACEHOLDER.sub(lambda match: placeholders[match["name"]], line)
        if _PLACEHOLDER.search(line) and not rendered.strip():
            continue
        lines.append(rendered)
    return "".join(lines)


def _title(request: ScaffoldRequest) -> str:
    if request.title is None:
        return " ".join(word.capitalize() for word in request.slug.split("-"))
    if not request.title.strip():
        raise UsageError("--title must not be blank")
    return request.title.strip()


def _patterns(pattern: str | None, track: Track) -> tuple[str, ...]:
    if pattern is None:
        if track is Track.DSA:
            raise UsageError("track dsa needs a primary pattern: add --pattern")
        return ()
    if pattern not in PATTERNS:
        raise UsageError(f'unknown pattern "{pattern}"; see docs/specs/content.md')
    return (pattern,)
