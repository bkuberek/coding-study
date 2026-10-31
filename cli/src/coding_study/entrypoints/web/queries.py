"""The query parameters of the API's reads, taking the values the matching `cstudy` options take
(docs/specs/web-ui.md#endpoints). A value outside them is a usage error, 422 `usage`."""

from enum import StrEnum

from starlette.datastructures import QueryParams

from coding_study.domain.errors import UsageError

TRUE = "true"
FALSE = "false"


def choice[Choice: StrEnum](query: QueryParams, name: str, choices: type[Choice]) -> Choice | None:
    value = query.get(name)
    return None if value is None else _choice(name, value, choices)


def choice_list[Choice: StrEnum](
    query: QueryParams, name: str, choices: type[Choice]
) -> tuple[Choice, ...]:
    """A repeatable parameter, as `--track` repeats: `?track=dsa&track=lld`."""
    return tuple(_choice(name, value, choices) for value in query.getlist(name))


def switch(query: QueryParams, name: str) -> bool:
    """`true` or `false`; false when absent, as a flag left off."""
    value = query.get(name, FALSE)
    if value not in (TRUE, FALSE):
        raise UsageError(f'invalid {name} "{value}": use {TRUE} or {FALSE}')
    return value == TRUE


def positive_integer(query: QueryParams, name: str) -> int | None:
    value = query.get(name)
    if value is None:
        return None
    if not value.isdecimal() or int(value) < 1:
        raise UsageError(f'invalid {name} "{value}": use a positive integer')
    return int(value)


def _choice[Choice: StrEnum](name: str, value: str, choices: type[Choice]) -> Choice:
    try:
        return choices(value)
    except ValueError:
        known = ", ".join(choices)
        raise UsageError(f'invalid {name} "{value}": use one of {known}') from None
