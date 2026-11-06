"""A new `progress_db` moves nothing (docs/specs/cli.md#configuration): the old file stays where it
is, and `cstudy` uses the file at the new path or starts an empty one there. The page and
`cstudy config edit` say so in these words."""

from coding_study.application.environment import Environment
from coding_study.domain.config import DEFAULT_PROGRESS_DB


def progress_db_notice(current: str, new: str, is_there: bool | None) -> str:
    """`is_there`: whether a file is at the new path; None outside a workspace, which it is
    relative to."""
    moved = f"Changing progress_db does not move your data: it stays in {current}."
    if is_there is None:
        return f"{moved} The new path, {new}, is relative to each workspace's root."
    if is_there:
        return f"{moved} A database exists at {new}, and cstudy will use it."
    return f"{moved} No database exists at {new}, so cstudy will start an empty one there."


def progress_db_question(environment: Environment, value: object) -> str | None:
    """What to ask before `value`, as a change of `progress_db` holds it (null returns it to its
    default), replaces the path in force; None when it changes nothing, or when the parser will
    refuse it."""
    new = DEFAULT_PROGRESS_DB if value is None else value
    current = environment.config.progress_db
    if not isinstance(new, str) or not new or new == current:
        return None
    notice = progress_db_notice(current, new, environment.workspace.exists(new))
    return f"{notice} Change it?"
