"""JSON values as the runner reads and writes them."""

from typing import TypeIs

type Json = bool | int | float | str | list[Json] | dict[str, Json] | None


def is_int(value: object) -> TypeIs[int]:
    """True for integers but not booleans, which Python treats as integers."""
    return isinstance(value, int) and not isinstance(value, bool)


def type_name(value: object) -> str:
    return "None" if value is None else type(value).__name__
