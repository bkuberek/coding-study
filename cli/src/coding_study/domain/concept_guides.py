"""Concept guides and learning paths (docs/specs/guides.md): what they are, and how far a learner
has come along a path.

Not to be confused with `domain/guides.py`, the published documentation that messages link to, or
with the user's own study guides of `study_guides.root`.
"""

import difflib
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.labels import LabelFilter, Labels
from coding_study.domain.profile import (
    GUIDE_DIMENSIONS,
    NO_WIDENING,
    Dimension,
    Profile,
    Widening,
)
from coding_study.domain.scheduling import ProblemStatus

GUIDES_DIRECTORY = "guides"
PATHS_DIRECTORY = "paths"
"""Inside `guides/`; reserved, so no guide may take it as its slug."""
GUIDE_FILE = "guide.md"
GUIDE_META_FILE = "meta.yaml"
EXAMPLES_DIRECTORY = "examples"
DIAGRAMS_DIRECTORY = "diagrams"
"""The light and dark SVG drawings of a guide's diagrams (docs/specs/guides.md#svg-drawings)."""
PATH_SUFFIX = ".yaml"
MAX_SLUG_LENGTH = 64
_SLUG = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
_SUGGESTIONS = 3
_SUGGESTION_CUTOFF = 0.6
FIRST_LEVEL = 1


class GuideLevel(StrEnum):
    INTRO = "intro"
    CORE = "core"
    ADVANCED = "advanced"


LEVEL_RANKS: Mapping[GuideLevel, int] = {
    GuideLevel.INTRO: 1,
    GuideLevel.CORE: 2,
    GuideLevel.ADVANCED: 3,
}
"""A guide level as a number, from introductory to advanced, for a path's level and order."""
_LEVELS_BY_RANK = {rank: level for level, rank in LEVEL_RANKS.items()}


class GuideStatus(StrEnum):
    """`cstudy learn --status`: a guide read once marked; a path read once all its guides are."""

    READ = "read"
    NOT_READ = "not_read"


@dataclass(frozen=True, slots=True)
class GuideMeta:
    slug: str
    """The guide's folder name."""
    title: str
    summary: str
    level: GuideLevel
    domains: tuple[str, ...] = ()
    """What the guide is about (docs/specs/guides.md#labels)."""
    job_roles: tuple[str, ...] = ()
    """Who it is for, `general` for any engineer."""
    prerequisites: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()
    """The problems that practice the guide, in the order to try them."""
    shell: bool = False
    """Its topic is the shell, so its examples may have a bash variant
    (docs/specs/guides.md#shell-guides)."""


class StepKind(StrEnum):
    GUIDE = "guide"
    PROBLEM = "problem"


@dataclass(frozen=True, slots=True)
class PathStep:
    kind: StepKind
    slug: str
    level: int | None = None
    """A problem step's level target: done once this level passes; None: once it passes."""

    @classmethod
    def guide(cls, slug: str) -> "PathStep":
        return cls(StepKind.GUIDE, slug)

    @classmethod
    def problem(cls, slug: str, level: int | None = None) -> "PathStep":
        return cls(StepKind.PROBLEM, slug, level)


@dataclass(frozen=True, slots=True)
class LearningPath:
    slug: str
    """The file's name without `.yaml`."""
    title: str
    summary: str
    steps: tuple[PathStep, ...]
    level: GuideLevel | None = None
    """The level the path names; None takes it from its guides (docs/specs/guides.md#path-order)."""


@dataclass(frozen=True, slots=True)
class ProblemFacts:
    """What progress.db says of a problem a path names."""

    title: str
    status: ProblemStatus
    passed: bool
    """At least one passed attempt, through every level for a problem with levels, as a set's
    entry without a target counts it, whatever the review schedule says now."""
    level_passed: int | None
    """The highest level an attempt has passed; None for a problem without levels."""


@dataclass(frozen=True, slots=True)
class StepProgress:
    step: PathStep
    title: str
    done: bool
    status: str
    """As `cstudy learn --path` writes it: `read`, `passed`, `level 2 passed`, `in progress`."""
    level_passed: int | None = None


def path_level(path: LearningPath, levels: Mapping[str, GuideLevel]) -> GuideLevel | None:
    """The level a path is for (docs/specs/guides.md#path-order): the one it names, or else the
    level nearest the mean of its guide steps' levels, the higher one when the mean is halfway
    between two. `levels` holds each guide's level by slug; problem steps, and guides it does not
    hold, do not count. None for a path that names none and has no such guides."""
    if path.level is not None:
        return path.level
    ranks = _guide_ranks(path, levels)
    if not ranks:
        return None
    # Rounds the mean half up: floor(sum / n + 1/2), in integers.
    return _LEVELS_BY_RANK[(2 * sum(ranks) + len(ranks)) // (2 * len(ranks))]


def by_level(
    paths: Iterable[LearningPath], levels: Mapping[str, GuideLevel]
) -> tuple[LearningPath, ...]:
    """The paths from introductory to advanced (docs/specs/guides.md#path-order): by
    `path_level`, then by the mean of their guides' levels, lowest first; paths alike in both keep
    their order, a path without guides comes after the others of its level, and a path with no
    level at all comes last."""

    def rank(path: LearningPath) -> tuple[bool, int, bool, Fraction]:
        level = path_level(path, levels)
        ranks = _guide_ranks(path, levels)
        mean = Fraction(sum(ranks), len(ranks)) if ranks else Fraction(0)
        return (level is None, 0 if level is None else LEVEL_RANKS[level], not ranks, mean)

    return tuple(sorted(paths, key=rank))


def guide_labels(meta: GuideMeta) -> Labels:
    """What a guide says it is about and who it is for, as the profile reads an entry."""
    return Labels(domains=meta.domains, job_roles=meta.job_roles)


def explicit_widening(explicit: LabelFilter, widening: Widening = NO_WIDENING) -> Widening:
    """`--widen`, plus the dimension of each explicit `--domain` or `--role`, which replaces the
    profile there (docs/specs/cli.md#explicit-filters-and-widening)."""
    dimensions = {
        Dimension.DOMAINS: explicit.domain is not None,
        Dimension.JOB_ROLES: explicit.role is not None,
    }
    return widening.plus(*(dimension for dimension, given in dimensions.items() if given))


def labels_listed(
    labels: Iterable[Labels],
    profile: Profile,
    explicit: LabelFilter = LabelFilter(),  # noqa: B008 - frozen, so one shared default is safe
    widening: Widening = NO_WIDENING,
) -> bool:
    """Whether a guide, with one `Labels`, or a path, with those of its steps, is listed: an
    explicit `--domain` or `--role` matches by what the entry lists, and the profile's roles and
    domains, unless one of those flags or `--widen` replaced them, by the rule of
    docs/specs/cli.md#matching. A path matches when one of its steps does; a guide has no
    language, so the profile's languages never apply. With nothing to apply, everything is listed,
    a path without steps included."""
    applied = explicit_widening(explicit, widening)
    if not explicit.is_set and not profile.active(GUIDE_DIMENSIONS, applied):
        return True
    return any(
        explicit.matches(entry)
        and profile.matches(entry, applies=GUIDE_DIMENSIONS, widening=applied)
        for entry in labels
    )


def search_words(text: str) -> tuple[str, ...]:
    """The words of a search, in lower case (docs/specs/cli.md#cstudy-learn)."""
    return tuple(text.lower().split())


def matches_search(words: Sequence[str], *fields: str) -> bool:
    """Every word is in one of the fields, in any case: the rule of `cstudy learn --search` and of
    the Guides page's search (`tools/web-ui/src/page/guides-model.ts`)."""
    lowered = [field.lower() for field in fields]
    return all(any(word in field for field in lowered) for word in words)


def _guide_ranks(path: LearningPath, levels: Mapping[str, GuideLevel]) -> list[int]:
    return [
        LEVEL_RANKS[levels[step.slug]]
        for step in path.steps
        if step.kind is StepKind.GUIDE and step.slug in levels
    ]


def is_slug(name: str) -> bool:
    """A kebab-case slug: a lowercase letter first, then lowercase letters, digits and single
    hyphens, at most 64 characters."""
    return len(name) <= MAX_SLUG_LENGTH and _SLUG.fullmatch(name) is not None


def guide_step_progress(step: PathStep, title: str, read: bool) -> StepProgress:
    return StepProgress(step, title, done=read, status="read" if read else "not read")


def problem_step_progress(step: PathStep, facts: ProblemFacts) -> StepProgress:
    """docs/specs/guides.md#reading-progress"""
    level = facts.level_passed or 0
    target = step.level
    done = facts.passed or (target is not None and level >= target)
    if facts.passed:
        status = "passed"
    elif level > 0:
        status = f"level {level} passed"
    else:
        status = facts.status.label
    return StepProgress(step, facts.title, done, status, facts.level_passed)


def highest_level_passed(attempts: Iterable[Attempt], levels: int) -> int | None:
    """An attempt that has unlocked level n passed levels 1 to n - 1; a passed attempt passed
    the levels `cstudy done` recorded, or all of them when it recorded none. None for a problem
    without levels."""
    if levels == 0:
        return None
    reached = 0
    for attempt in attempts:
        if attempt.status is AttemptStatus.PASSED:
            recorded = attempt.levels_passed
            reached = max(reached, levels if recorded is None else recorded)
        if attempt.level_unlocked is not None:
            reached = max(reached, attempt.level_unlocked - FIRST_LEVEL)
    return min(reached, levels)


def unknown_slug_message(noun: str, slug: str, known: Sequence[str]) -> str:
    """`unknown guide "x"; did you mean y?`, or where to find the list."""
    near = difflib.get_close_matches(slug, list(known), _SUGGESTIONS, _SUGGESTION_CUTOFF)
    hint = f"did you mean {', '.join(near)}?" if near else f"cstudy learn lists the {noun}s"
    return f'unknown {noun} "{slug}"; {hint}'
