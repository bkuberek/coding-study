"""The web UI's preferences, the one file the page owns (docs/specs/web-ui.md#preferences)."""

from dataclasses import asdict, dataclass, fields
from enum import StrEnum
from typing import cast

from coding_study.domain.errors import UsageError

PREFERENCES_FORMAT = 1
FORMAT_KEY = "format"
THEME_KEY = "theme"


class Theme(StrEnum):
    SYSTEM = "system"
    """Light or dark as the browser's `prefers-color-scheme` says."""
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True, slots=True)
class Preferences:
    vim: bool = False
    """Vim keybindings in every editor."""
    run_on_save: bool = False
    """A save, or a change on disk in the attempt's files, runs the tests again."""
    typecheck: bool = True
    """TypeScript runs type-check, so type errors reach the editor as markers."""
    theme: Theme = Theme.SYSTEM
    code_intelligence: bool = False
    """Live diagnostics, hover and go to definition from language servers (ADR 0018)."""
    autocomplete: bool = False
    """Completion and signature help, all of it: applies only while `code_intelligence` is on, but
    is stored as set, so turning code intelligence off keeps it."""


PREFERENCE_KEYS = tuple(field.name for field in fields(Preferences))
THEMES = ", ".join(Theme).rpartition(", ")


def preferences_document(preferences: Preferences) -> dict[str, object]:
    """`{"format": 1, "vim": false, "run_on_save": false, "typecheck": true, "theme": "system",
    "code_intelligence": false, "autocomplete": false}`."""
    document = asdict(preferences)
    return {FORMAT_KEY: PREFERENCES_FORMAT, **document, THEME_KEY: preferences.theme.value}


def parse_preferences(document: object) -> Preferences:
    """A document as `preferences_document` writes it; a key it leaves out keeps its default.

    Raises UsageError for anything else: not an object, an unknown key, another format, a theme
    other than `system`, `light` and `dark`, or another preference that is not a boolean."""
    if not isinstance(document, dict):
        raise UsageError("preferences must be a JSON object")
    values = dict(cast(dict[str, object], document))
    _check_format(values.pop(FORMAT_KEY, PREFERENCES_FORMAT))
    theme = _theme(values.pop(THEME_KEY, Theme.SYSTEM.value))
    switches = {key: _switch(key, value) for key, value in values.items()}
    return Preferences(**switches, theme=theme)


def _switch(key: str, value: object) -> bool:
    if key not in PREFERENCE_KEYS:
        raise UsageError(f'unknown preference "{key}"')
    if not isinstance(value, bool):
        raise UsageError(f'preference "{key}" must be true or false')
    return value


def _theme(value: object) -> Theme:
    if isinstance(value, str) and value in tuple(Theme):
        return Theme(value)
    first, _, last = THEMES
    raise UsageError(f'preference "{THEME_KEY}" must be {first} or {last}')


def _check_format(value: object) -> None:
    """Exactly the integer 1: JSON `true` and `1.0` compare equal to it in Python."""
    if type(value) is not int or value != PREFERENCES_FORMAT:
        raise UsageError(f"preferences format must be {PREFERENCES_FORMAT}")
