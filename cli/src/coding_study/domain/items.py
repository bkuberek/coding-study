"""Non-autograded items: system design and code review prompts with a rubric and a reference.

They live in `tracks/<track>/<slug>/` (docs/specs/content.md#non-autograded-item-format). The
user answers in a notes file; `cstudy done` takes a self-graded rating. The rubric file name is
`coding_study.domain.problem_files.RUBRIC_FILE`, shared with `lld` problems.
"""

from dataclasses import dataclass

from coding_study.domain.problem import DEFAULT_CURRICULUM_ORDER, ContentStatus, Difficulty, Track

ITEM_FILE = "item.yaml"
PROMPT_FILE = "prompt.md"
REFERENCE_FILE = "reference.md"
TEMPLATE_FILE = "template.md"
CHANGE_FILE = "change.diff"
"""Code review only: the change under review, or `files/` instead."""
CHANGE_DIRECTORY = "files"
ITEM_TRACKS = (Track.SYSTEM_DESIGN, Track.CODE_REVIEW)
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
    """item.yaml, validated by schemas/item.schema.json."""

    slug: str
    title: str
    track: Track
    difficulty: Difficulty
    estimate_minutes: int
    status: ContentStatus
    order: int = DEFAULT_CURRICULUM_ORDER
    references: ItemReferences = ItemReferences()
    related: tuple[str, ...] = ()
