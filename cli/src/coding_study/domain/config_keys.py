"""What the Settings view shows of each key of the user config (docs/specs/web-ui.md#settings-view).

The parser's module holds the keys, so a new key can't be forgotten: this is only their shape.
"""

from dataclasses import dataclass
from enum import StrEnum


class KeyKind(StrEnum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    TEXT = "text"
    CHOICE = "choice"
    """One of `choices`."""
    CHOICES = "choices"
    """A list of `choices`."""


type KeyValue = bool | int | str | list[str] | None


@dataclass(frozen=True, slots=True)
class ConfigKey:
    name: str
    """Dotted: `schedule.max_interval_days`; a top-level key has no dot."""
    kind: KeyKind
    default: KeyValue
    """None: unset by default."""
    help: str
    applies: str
    """When a change takes effect, in words."""
    choices: tuple[str, ...] = ()
    example: KeyValue = None
    """What a key without a default may hold."""
    reserved: bool = False
    """Accepted in the file, and does nothing yet."""

    @property
    def table(self) -> str:
        """Empty for a top-level key."""
        return self.name.rpartition(".")[0]

    @property
    def short_name(self) -> str:
        return self.name.rpartition(".")[2]


@dataclass(frozen=True, slots=True)
class ConfigKeyState:
    key: ConfigKey
    value: object
    """As the file holds it; the default when it does not hold the key."""
    is_set: bool


@dataclass(frozen=True, slots=True)
class ConfigView:
    """The config file as it is now."""

    location: str
    exists: bool
    writable: bool
    """False when the file does not parse, so nothing may overwrite it."""
    issues: tuple[str, ...]
    """What keeps it from loading, as `cstudy` words it."""
    keys: tuple[ConfigKeyState, ...]
