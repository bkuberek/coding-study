"""`cstudy show`: the rendered statement (docs/specs/cli.md#cstudy-show).

Progressive problems show the levels the attempt in progress has unlocked (level 1 without one),
or levels 1 to `--level`. Non-autograded items show their rendered prompt.
"""

from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.item_statement_file import guide_links, item_statement_text
from coding_study.application.practice_catalog import is_item
from coding_study.application.statement_file import statement_text
from coding_study.domain.errors import UsageError
from coding_study.domain.levels import level_run


@dataclass(frozen=True, slots=True)
class ShowRequest:
    slug: str
    level: int | None = None
    """Progressive problems: show levels 1 to `level`; None shows every unlocked level."""


def show_statement(environment: Environment, request: ShowRequest) -> str:
    if is_item(environment, request.slug):
        return _item_statement(environment, request)
    problem = environment.problems.load(request.slug)
    attempt = environment.progress.active_attempt(request.slug)
    try:
        levels = level_run(problem.meta, attempt.level_unlocked if attempt else None, request.level)
    except ValueError as error:
        raise UsageError(str(error)) from None
    return statement_text(environment, problem, levels.ran_up_to if levels else None)


def _item_statement(environment: Environment, request: ShowRequest) -> str:
    meta = environment.items.load(request.slug)
    if request.level is not None:
        raise UsageError(f"{meta.slug} has no levels")
    return item_statement_text(environment, meta, guide_links(environment, meta))
