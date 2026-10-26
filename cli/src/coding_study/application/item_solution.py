"""`cstudy solution` for a non-autograded item: its rubric, then its reference answer.

Self-review against the reference is the point of an item, so revealing it never lowers the
grade (docs/specs/progress-and-scheduling.md#grade); an attempt in progress still records it.
"""

from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.mock_interview import require_no_running_mock
from coding_study.domain.items import REFERENCE_FILE, ItemMeta
from coding_study.domain.problem_files import RUBRIC_FILE


@dataclass(frozen=True, slots=True)
class ItemSolutionView:
    meta: ItemMeta
    rubric: str | None
    """rubric.md, or None when the file does not exist."""
    reference: str | None


def reveal_item_solution(environment: Environment, slug: str) -> ItemSolutionView:
    """Also sets `solution_revealed` on the item's attempt in progress; raises UsageError during
    a mock interview."""
    require_no_running_mock(environment, "cstudy solution")
    meta = environment.items.load(slug)
    attempt = environment.progress.active_attempt(slug)
    if attempt is not None and not attempt.solution_revealed:
        environment.progress.update_attempt(replace(attempt, solution_revealed=True))
    return ItemSolutionView(
        meta,
        rubric=environment.items.read_text(slug, RUBRIC_FILE),
        reference=environment.items.read_text(slug, REFERENCE_FILE),
    )
