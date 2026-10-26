"""`cstudy hint`: reveal the next hint of the attempt in progress (docs/specs/cli.md#cstudy-hint).

The attempt's `hints_used` counts the hints revealed so far, so the next one is hint
`hints_used + 1`; any hint caps the grade at `ok` (progress-and-scheduling.md#grade).
"""

from dataclasses import dataclass, replace

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.mock_interview import require_no_running_mock
from coding_study.domain.hints import problem_hints
from coding_study.domain.problem_files import PROBLEM_FILE


@dataclass(frozen=True, slots=True)
class RevealedHint:
    slug: str
    number: int
    """From 1."""
    total: int
    text: str


def reveal_hint(environment: Environment, slug: str | None) -> RevealedHint | None:
    """None when every hint is already revealed; raises UsageError without an attempt or during
    a mock interview."""
    require_no_running_mock(environment, "cstudy hint")
    attempt = find_attempt(environment.progress, slug, None)
    hints = problem_hints(environment.files.read_text(attempt.slug, PROBLEM_FILE) or "")
    if attempt.hints_used >= len(hints):
        return None
    number = attempt.hints_used + 1
    environment.progress.update_attempt(replace(attempt, hints_used=number))
    return RevealedHint(attempt.slug, number, len(hints), hints[number - 1])
