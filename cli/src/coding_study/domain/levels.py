"""Progressive and project problems unlock their levels one at a time.

Spec: docs/specs/problem-format.md#progressive-problems. An attempt stores its highest unlocked
level; `cstudy test` runs the cases of every unlocked level, and a run that passes all of them
unlocks the next one.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import assert_never

from coding_study.domain.cases import Case
from coding_study.domain.problem import Level, ProblemKind, ProblemMeta

FIRST_LEVEL = 1
_LEVEL_HEADING = re.compile(r"Level (?P<number>\d+): \S.*")


@dataclass(frozen=True, slots=True)
class LevelProgress:
    """Levels 1 to `unlocked` are open; the rest stay hidden until earlier ones pass."""

    levels: tuple[Level, ...]
    unlocked: int

    @property
    def last(self) -> int:
        return len(self.levels)

    @property
    def all_unlocked(self) -> bool:
        return self.unlocked >= self.last

    @property
    def locked(self) -> tuple[int, ...]:
        return tuple(range(self.unlocked + 1, self.last + 1))

    def title(self, number: int) -> str:
        return next(level.title for level in self.levels if level.number == number)

    def after_passing(self) -> "LevelProgress":
        """Passing every unlocked level opens the next one."""
        return self if self.all_unlocked else replace(self, unlocked=self.unlocked + 1)

    def run_level(self, requested: int | None) -> int:
        """The highest level a run covers: `requested`, or every unlocked level.

        Raises ValueError for a level the problem lacks or one still locked.
        """
        if requested is None:
            return self.unlocked
        if not FIRST_LEVEL <= requested <= self.last:
            raise ValueError(f"no level {requested}; levels are {FIRST_LEVEL} to {self.last}")
        if requested > self.unlocked:
            raise ValueError(
                f"level {requested} is locked; pass level {self.unlocked} with cstudy test first"
            )
        return requested


@dataclass(frozen=True, slots=True)
class LevelRun:
    """The levels one run covers, 1 to `ran_up_to`, and where the attempt stands."""

    ran_up_to: int
    progress: LevelProgress
    newly_unlocked: bool = False
    """The run unlocked `progress.unlocked`."""

    @property
    def unlocked(self) -> int:
        return self.progress.unlocked

    def after_passing(self) -> "LevelRun":
        """A pass of every unlocked level opens the next one; a pass of fewer opens nothing."""
        if self.ran_up_to != self.progress.unlocked:
            return self
        progress = self.progress.after_passing()
        return LevelRun(self.ran_up_to, progress, newly_unlocked=progress != self.progress)


def level_run(meta: ProblemMeta, unlocked: int | None, requested: int | None) -> LevelRun | None:
    """The levels a run or a statement covers; None for problems without levels.

    Raises ValueError when `requested` names a level on a problem without levels, a level the
    problem lacks, or a locked one.
    """
    progress = level_progress(meta, unlocked)
    if progress is None:
        if requested is not None:
            raise ValueError(f"{meta.slug} has no levels")
        return None
    return LevelRun(progress.run_level(requested), progress)


def has_levels(kind: ProblemKind) -> bool:
    """Whether problems of `kind` open their levels one at a time."""
    match kind:
        case ProblemKind.PROGRESSIVE | ProblemKind.PROJECT:
            return True
        case ProblemKind.FUNCTION | ProblemKind.DESIGN | ProblemKind.CONCURRENT:
            return False
        case _:
            assert_never(kind)


def level_progress(meta: ProblemMeta, unlocked: int | None) -> LevelProgress | None:
    """None for problems without levels; an attempt that stored no level has level 1 open."""
    if not has_levels(meta.kind) or not meta.levels:
        return None
    stored = max(unlocked or FIRST_LEVEL, FIRST_LEVEL)
    return LevelProgress(meta.levels, min(stored, len(meta.levels)))


def cases_up_to(cases: Iterable[Case], level: int) -> tuple[Case, ...]:
    """The cases of levels 1 to `level`, in tests.json order."""
    return tuple(case for case in cases if case.level is not None and case.level <= level)


def level_heading(title: str) -> int | None:
    """The level number of a `## Level <n>: <title>` heading in problem.md, else None."""
    heading = _LEVEL_HEADING.fullmatch(title)
    return int(heading["number"]) if heading else None
