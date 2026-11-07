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
class KeyTitle:
    """What Settings calls a key. Its own name stays beside it: the CLI and the file use that."""

    label: str
    section: str
    """Related keys together, whichever tables of the file they live in."""


_GENERAL = "general"
_RUNS = "runs"
_BENCHMARKS = "benchmarks"
_SCHEDULE = "review schedule"
KEY_TITLES = {
    "default_lang": KeyTitle("Default language", _GENERAL),
    "open_on_start": KeyTitle("Open my editor on start", _GENERAL),
    "progress_db": KeyTitle("Progress database", _GENERAL),
    "next.tracks": KeyTitle("Tracks to pick from", _GENERAL),
    "done.auto_commit": KeyTitle("Commit on done", _GENERAL),
    "study_guides.root": KeyTitle("Study guides folder", _GENERAL),
    "time_limit.enabled": KeyTitle("Apply time limits", _RUNS),
    "time_limit.value": KeyTitle("Time limit", _RUNS),
    "time_limit.floor_ms": KeyTitle("Lowest time limit, in ms", _RUNS),
    "hang_guard.ms": KeyTitle("Hang guard, in ms", _RUNS),
    "bench.reps": KeyTitle("Repetitions per size", _BENCHMARKS),
    "bench.memory": KeyTitle("Measure memory", _BENCHMARKS),
    "schedule.penalize_suboptimal": KeyTitle("Cap the grade of a suboptimal run", _SCHEDULE),
    "schedule.max_interval_days": KeyTitle("Longest interval, in days", _SCHEDULE),
    "schedule.again_interval_days": KeyTitle("After an again, in days", _SCHEDULE),
    "schedule.hard_first_interval_days": KeyTitle("After a first hard, in days", _SCHEDULE),
    "schedule.ok_first_interval_days": KeyTitle("After a first ok, in days", _SCHEDULE),
    "schedule.ok_second_interval_days": KeyTitle("After a second ok, in days", _SCHEDULE),
    "schedule.easy_first_interval_days": KeyTitle("After a first easy, in days", _SCHEDULE),
    "schedule.easy_second_interval_days": KeyTitle("After a second easy, in days", _SCHEDULE),
    "schedule.mastered_interval_days": KeyTitle("Mastered from, in days", _SCHEDULE),
}
"""By key name. A test holds it equal to the keys the parser reads."""


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
