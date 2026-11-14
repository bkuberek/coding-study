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


@dataclass(frozen=True, slots=True)
class GuideMeta:
    slug: str
    """The guide's folder name."""
    title: str
    summary: str
    level: GuideLevel
    prerequisites: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()
    """The problems that practise the guide, in the order to try them."""


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
    """The level a path is for (docs/specs/guides.md#path-order): the level nearest the mean of
    its guide steps' levels, the higher one when the mean is halfway between two. `levels` holds
    each guide's level by slug; problem steps, and guides it does not hold, do not count. None for
    a path without such guides."""
    ranks = _guide_ranks(path, levels)
    if not ranks:
        return None
    # Rounds the mean half up: floor(sum / n + 1/2), in integers.
    return _LEVELS_BY_RANK[(2 * sum(ranks) + len(ranks)) // (2 * len(ranks))]


def by_level(
    paths: Iterable[LearningPath], levels: Mapping[str, GuideLevel]
) -> tuple[LearningPath, ...]:
    """The paths from introductory to advanced (docs/specs/guides.md#path-order): by the mean of
    their guides' levels, lowest first, which orders them by `path_level` too; paths with the same
    mean keep their order, and a path without guides comes last."""

    def mean_rank(path: LearningPath) -> tuple[bool, Fraction]:
        ranks = _guide_ranks(path, levels)
        return (not ranks, Fraction(sum(ranks), len(ranks)) if ranks else Fraction(0))

    return tuple(sorted(paths, key=mean_rank))


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
