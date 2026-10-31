"""`cstudy hint`: reveal the next hint of the attempt in progress (docs/specs/cli.md#cstudy-hint).

The attempt's `hints_used` counts the hints revealed so far, so the next one is hint
`hints_used + 1`; any hint caps the grade at `ok` (progress-and-scheduling.md#grade). A project
problem shows only the hints of its unlocked levels (`hints.hint_level`).
"""

from dataclasses import dataclass, replace

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.mock_interview import require_no_running_mock
from coding_study.domain.attempts import Attempt
from coding_study.domain.hints import hint_level, problem_hints
from coding_study.domain.levels import level_progress
from coding_study.domain.problem import ProblemKind
from coding_study.domain.problem_files import PROBLEM_FILE


@dataclass(frozen=True, slots=True)
class RevealedHint:
    slug: str
    number: int
    """From 1."""
    total: int
    text: str


@dataclass(frozen=True, slots=True)
class HintsLocked:
    """A project problem's next hint belongs to a level that is still locked."""

    slug: str
    level: int
    """The level whose opening reveals the next hint."""


def reveal_hint(environment: Environment, slug: str | None) -> RevealedHint | HintsLocked | None:
    """None when every hint is already revealed; raises UsageError without an attempt or during
    a mock interview."""
    require_no_running_mock(environment, "cstudy hint")
    attempt = find_attempt(environment.progress, slug, None)
    hints = problem_hints(environment.files.read_text(attempt.slug, PROBLEM_FILE) or "")
    if attempt.hints_used >= len(hints):
        return None
    number = attempt.hints_used + 1
    locked = _locked_level(environment, attempt, number, len(hints))
    if locked is not None:
        return HintsLocked(attempt.slug, locked)
    environment.progress.update_attempt(replace(attempt, hints_used=number))
    return RevealedHint(attempt.slug, number, len(hints), hints[number - 1])


def _locked_level(
    environment: Environment, attempt: Attempt, number: int, hint_count: int
) -> int | None:
    """The locked level hint `number` of a project problem opens with; None when it is open."""
    if attempt.language is None:
        return None
    meta = environment.problems.load(attempt.slug).meta
    levels = level_progress(meta, attempt.level_unlocked)
    if meta.kind is not ProblemKind.PROJECT or levels is None:
        return None
    level = hint_level(number, hint_count, levels.last)
    return level if level > levels.unlocked else None
