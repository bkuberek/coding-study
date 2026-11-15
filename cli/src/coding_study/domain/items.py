"""Rubric-checked problems: system design and code review prompts with a rubric and a reference.

They live in `problems/<slug>/` (docs/specs/content.md#rubric-checked-problems). The user answers
in a notes file; `cstudy done` takes a self-graded rating. The rubric file name is
`coding_study.domain.problem_files.RUBRIC_FILE`, shared with `lld` problems.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from coding_study.domain.labels import Labels
from coding_study.domain.problem import (
    DEFAULT_CURRICULUM_ORDER,
    NO_PATTERN_RANK,
    ContentStatus,
    Difficulty,
    ListingKey,
    ProblemKind,
    Track,
    track_rank,
)

PROMPT_FILE = "prompt.md"
REFERENCE_FILE = "reference.md"
TEMPLATE_FILE = "template.md"
CHANGE_FILE = "change.diff"
"""Code review only: the change under review, or `files/` instead."""
CHANGE_DIRECTORY = "files"
REFERENCE_TITLE_SUFFIX = ": Reference"
NOTES_TITLE_SUFFIX = ": Notes"
GUIDE_ANCHOR = "#"


@dataclass(frozen=True, slots=True)
class ItemReferences:
    study_guides: tuple[str, ...] = ()
    """Paths relative to the user's study-guides root (config `study_guides.root`), each with
    an optional `#section` anchor, such as `system-design.md#caching`; never copied."""
    links: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GuideLink:
    """A study-guide reference whose file exists under the user's study-guides root."""

    reference: str
    """As written in `references.study_guides`."""
    location: str
    """The guide file, such as `file:///home/me/study-guides/system-design.md`."""

    @property
    def target(self) -> str:
        """The location with the reference's `#section` anchor."""
        _, anchor_separator, anchor = self.reference.partition(GUIDE_ANCHOR)
        return f"{self.location}{anchor_separator}{anchor}"


def guide_path(reference: str) -> str:
    """The guide file a study-guide reference names, without its `#section` anchor."""
    return reference.partition(GUIDE_ANCHOR)[0]


@dataclass(frozen=True, slots=True)
class ItemMeta:
    """The meta.yaml of a rubric-checked problem, validated by schemas/meta.schema.json."""

    slug: str
    title: str
    track: Track
    difficulty: Difficulty
    estimate_minutes: int
    status: ContentStatus
    order: int = DEFAULT_CURRICULUM_ORDER
    labels: Labels = field(default_factory=Labels)
    """Domains, job roles and scope (check S24, docs/specs/content.md)."""
    references: ItemReferences = ItemReferences()
    related: tuple[str, ...] = ()

    @property
    def kind(self) -> "EntryKind":
        """A rubric problem has the track of its own kind's name."""
        return EntryKind(self.track.value)

    def listing_key(self) -> ListingKey:
        """The order of `cstudy list` (docs/specs/compatibility.md#order): a rubric problem is in
        the catalog and has no pattern, so it lists first in its track, by `order` and slug."""
        return (False, track_rank(self.track), NO_PATTERN_RANK, self.order, self.slug)


class EntryKind(StrEnum):
    """A catalog entry's `kind` in the CLI's JSON documents and `cstudy list --kind`: an autograded
    kind of problem, or a rubric kind."""

    FUNCTION = "function"
    DESIGN = "design"
    PROGRESSIVE = "progressive"
    CONCURRENT = "concurrent"
    PROJECT = "project"
    SYSTEM_DESIGN = "system-design"
    CODE_REVIEW = "code-review"


RUBRIC_KINDS = (EntryKind.SYSTEM_DESIGN, EntryKind.CODE_REVIEW)
"""The kinds checked by a rubric and graded by the user. Each has the track of its own name."""


def is_rubric_track(track: Track) -> bool:
    return any(track.value == kind.value for kind in RUBRIC_KINDS)


def entry_kind(kind: ProblemKind) -> EntryKind:
    return EntryKind(kind.value)
