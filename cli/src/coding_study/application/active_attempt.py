"""The attempt a command works on (docs/specs/cli.md#command-summary).

Commands with an optional `<slug>` default to the active attempt: the most recent attempt with
status `in_progress`. If none exists, they exit 3.
"""

from coding_study.application.ports import ProgressStore
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language


def find_attempt(progress: ProgressStore, slug: str | None, language: Language | None) -> Attempt:
    """The attempt in progress for `slug` (default: the active one), in `language` if given."""
    if slug is None:
        active = progress.active_attempt()
        if active is None:
            raise UsageError("no attempt in progress; start one with cstudy start <slug>")
        if language is None:
            return active
        slug = active.slug
    found = (
        progress.active_attempt(slug)
        if language is None
        else progress.in_progress_attempt(slug, language)
    )
    if found is None:
        start = f"cstudy start {slug}" + (f" --lang {language}" if language else "")
        where = f"{slug} in {language}" if language else slug
        raise UsageError(f"no attempt in progress for {where}; start one with {start}")
    return found


def autograded_language(attempt: Attempt) -> Language:
    if attempt.language is None:
        raise UsageError(f"{attempt.slug} is not autograded")
    return attempt.language
