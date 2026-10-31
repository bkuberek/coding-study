"""What the web UI checks before it starts a run or a job as a child `cstudy`
(docs/specs/web-ui.md#lifecycle, docs/specs/web-ui.md#jobs).

These refusals reach the page as HTTP errors instead of a stream, worded as the CLI words them; any
other refusal comes from the child itself.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.application.active_attempt import attempt_in_progress, autograded_language
from coding_study.application.environment import Environment
from coding_study.application.submit_project import require_project
from coding_study.domain.errors import UsageError
from coding_study.domain.levels import level_run
from coding_study.domain.problem import Language, ProblemKind

VERIFY_SCOPE = (
    "the page verifies your own problems; "
    "run cstudy verify in a content checkout for catalog problems"
)


class RunCommand(StrEnum):
    TEST = "test"
    SUBMIT = "submit"


@dataclass(frozen=True, slots=True)
class RunCheck:
    attempt_id: int
    command: RunCommand
    level: int | None = None


@dataclass(frozen=True, slots=True)
class RunSubject:
    """What the run's child command names."""

    slug: str
    language: Language
    kind: ProblemKind


def check_run(environment: Environment, check: RunCheck) -> RunSubject:
    """Raises UnknownAttemptError and AttemptEndedError for an attempt not in progress, and
    UsageError for an item, `submit` on a problem that is not a project, and a level the problem
    lacks or keeps locked."""
    attempt = attempt_in_progress(environment.progress, check.attempt_id)
    language = autograded_language(attempt)
    meta = environment.problems.load(attempt.slug).meta
    if check.command is RunCommand.SUBMIT:
        require_project(meta)
    try:
        level_run(meta, attempt.level_unlocked, check.level)
    except ValueError as error:
        raise UsageError(str(error)) from None
    return RunSubject(attempt.slug, language, meta.kind)


def check_verify_scope(environment: Environment, slugs: Sequence[str]) -> None:
    """Raises UnknownProblemError for a slug no problem has, and UsageError for a catalog
    problem: the page verifies the workspace's own problems only."""
    for slug in slugs:
        if not environment.problems.load(slug).meta.workspace:
            raise UsageError(VERIFY_SCOPE)
