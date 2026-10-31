"""The JSON bodies of the API's writes, taking the values the matching `cstudy` options take
(docs/specs/web-ui.md#endpoints). A body that is not an object, a missing required field, or a
value of another type or outside its range is a usage error, 422 `usage`."""

from collections.abc import Mapping
from enum import StrEnum
from typing import cast

from starlette.requests import Request

from coding_study.domain.errors import UsageError
from coding_study.entrypoints.web.responses import json_body

type Body = Mapping[str, object]


async def object_body(request: Request) -> Body:
    document = await json_body(request)
    if not isinstance(document, dict):
        raise UsageError("the request body is not a JSON object")
    return cast(Body, document)


def required_text(body: Body, name: str) -> str:
    value = optional_text(body, name)
    if value is None:
        raise UsageError(f"the request needs {name}")
    return value


def optional_text(body: Body, name: str) -> str | None:
    value = body.get(name)
    if value is None or isinstance(value, str):
        return value
    raise UsageError(f"invalid {name} {_shown(value)}: use a string")


def switch(body: Body, name: str) -> bool:
    """`true` or `false`; false when absent or null, as a flag left off."""
    value = body.get(name)
    if value is None or isinstance(value, bool):
        return bool(value)
    raise UsageError(f"invalid {name} {_shown(value)}: use true or false")


def optional_choice[Choice: StrEnum](body: Body, name: str, choices: type[Choice]) -> Choice | None:
    value = body.get(name)
    return None if value is None else _choice(name, value, choices)


def choice_list[Choice: StrEnum](
    body: Body, name: str, choices: type[Choice]
) -> tuple[Choice, ...]:
    """A list of values, as a repeatable option takes them; empty when absent or null."""
    values = body.get(name)
    if values is None:
        return ()
    if not isinstance(values, list):
        raise UsageError(f"invalid {name} {_shown(values)}: use a list")
    return tuple(_choice(name, value, choices) for value in cast(list[object], values))


def optional_integer(body: Body, name: str, bounds: tuple[int, int]) -> int | None:
    """An integer within `bounds`, both included; null when absent."""
    value = body.get(name)
    if value is None:
        return None
    low, high = bounds
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise UsageError(f"invalid {name} {_shown(value)}: use an integer from {low} to {high}")
    return value


def _choice[Choice: StrEnum](name: str, value: object, choices: type[Choice]) -> Choice:
    known = ", ".join(choices)
    if not isinstance(value, str):
        raise UsageError(f"invalid {name} {_shown(value)}: use one of {known}")
    try:
        return choices(value)
    except ValueError:
        raise UsageError(f'invalid {name} "{value}": use one of {known}') from None


def _shown(value: object) -> str:
    return f'"{value}"' if isinstance(value, str) else str(value).lower()
