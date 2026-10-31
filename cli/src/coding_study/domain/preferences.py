"""The web UI's preferences, the one file the page owns (docs/specs/web-ui.md#preferences)."""

from dataclasses import asdict, dataclass, fields
from typing import cast

from coding_study.domain.errors import UsageError

PREFERENCES_FORMAT = 1
FORMAT_KEY = "format"


@dataclass(frozen=True, slots=True)
class Preferences:
    vim: bool = False
    """Vim keybindings in every editor."""
    run_on_save: bool = False
    """A save, or a change on disk in the attempt's files, runs the tests again."""
    typecheck: bool = True
    """TypeScript runs type-check, so type errors reach the editor as markers."""


PREFERENCE_KEYS = tuple(field.name for field in fields(Preferences))


def preferences_document(preferences: Preferences) -> dict[str, object]:
    """`{"format": 1, "vim": false, "run_on_save": false, "typecheck": true}`."""
    return {FORMAT_KEY: PREFERENCES_FORMAT, **asdict(preferences)}


def parse_preferences(document: object) -> Preferences:
    """A document as `preferences_document` writes it; a key it leaves out keeps its default.

    Raises UsageError for anything else: not an object, an unknown key, another format or a
    preference that is not a boolean."""
    if not isinstance(document, dict):
        raise UsageError("preferences must be a JSON object")
    values = dict(cast(dict[str, object], document))
    _check_format(values.pop(FORMAT_KEY, PREFERENCES_FORMAT))
    return Preferences(**{key: _preference(key, value) for key, value in values.items()})


def _preference(key: str, value: object) -> bool:
    if key not in PREFERENCE_KEYS:
        raise UsageError(f'unknown preference "{key}"')
    if not isinstance(value, bool):
        raise UsageError(f'preference "{key}" must be true or false')
    return value


def _check_format(value: object) -> None:
    """Exactly the integer 1: JSON `true` and `1.0` compare equal to it in Python."""
    if type(value) is not int or value != PREFERENCES_FORMAT:
        raise UsageError(f"preferences format must be {PREFERENCES_FORMAT}")
