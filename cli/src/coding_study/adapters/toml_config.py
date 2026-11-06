"""The user config file (docs/specs/cli.md#configuration).

Location precedence: `CSTUDY_CONFIG`, then `$XDG_CONFIG_HOME/coding-study/config.toml`, then
`~/.config/coding-study/config.toml`. Every key is optional; omitted keys keep the defaults
defined in `coding_study.domain.config`.
"""

import json
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self, cast

from coding_study.adapters.fs_study_guides import HOME_PREFIX
from coding_study.domain.config import (
    BenchSettings,
    Config,
    DoneSettings,
    HangGuardSettings,
    NextSettings,
    ScheduleSettings,
    StudyGuideSettings,
    TimeLimitSettings,
)
from coding_study.domain.config_keys import ConfigKey, KeyKind
from coding_study.domain.errors import ConfigError
from coding_study.domain.problem import Language, Track
from coding_study.domain.scheduling import ReviewIntervals
from coding_study.domain.time_limits import TimeLimit, parse_time_limit

CONFIG_PATH_VARIABLE = "CSTUDY_CONFIG"
XDG_CONFIG_HOME_VARIABLE = "XDG_CONFIG_HOME"
CONFIG_FILE = Path("coding-study") / "config.toml"

TEMPLATE_HEADER = """\
# Your cstudy settings (docs/specs/cli.md#configuration). Every key is optional: each one below is
# commented out, at its default. Remove the leading # of a key to change it.
# `cstudy config edit` opens this file, and the Settings view of `cstudy serve` edits it too."""

type _Table = Mapping[str, object]


def config_path(environ: Mapping[str, str], home: Path) -> Path:
    explicit = environ.get(CONFIG_PATH_VARIABLE, "")
    if explicit:
        return Path(explicit).expanduser()
    config_home = Path(environ.get(XDG_CONFIG_HOME_VARIABLE, ""))
    if not config_home.is_absolute():
        config_home = home / ".config"
    return config_home / CONFIG_FILE


class TomlConfigSource:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def location(self) -> str:
        return str(self._path)

    def exists(self) -> bool:
        return self._path.is_file()

    def create_from_template(self) -> bool:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._path.open("x", encoding="utf-8") as file:
                file.write(config_template())
        except FileExistsError:
            return False
        return True

    def load(self) -> Config:
        if not self.exists():
            return Config()
        try:
            values = tomllib.loads(self._path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(self.location, [str(error)]) from None
        return config_from_mapping(values, self.location)


def config_from_mapping(values: _Table, source: str) -> Config:
    """Validate every key, collecting all issues before raising ConfigError."""
    config, issues = _parsed(values)
    if issues:
        raise ConfigError(source, issues)
    return config


def config_issues(values: _Table) -> tuple[str, ...]:
    """What keeps `values` from loading, as `config_from_mapping` words it."""
    return _parsed(values)[1]


def _parsed(values: _Table) -> tuple[Config, tuple[str, ...]]:
    issues: list[str] = []
    top = _TableReader(values, "", issues)
    config = _config(top)
    top.report_unknown_keys()
    return config, tuple(issues)


def parsed_key_names() -> frozenset[str]:
    """Every key the parser reads, by its dotted name."""
    top = _TableReader({}, "", [])
    _config(top)
    return top.read_key_names()


def config_template() -> str:
    """A file that loads as the defaults: each key commented out, with what it does. `cstudy config
    edit` writes it when the user has no config yet."""
    sections: dict[str, list[str]] = {}
    for key in CONFIG_KEYS:
        sections.setdefault(key.table, []).extend(_template_lines(key))
    lines = [TEMPLATE_HEADER, ""]
    for table, body in sections.items():
        lines.extend([f"[{table}]"] if table else [])
        lines.extend([*body, ""])
    return "\n".join(lines)


def _template_lines(key: ConfigKey) -> list[str]:
    shown = key.default if key.default is not None else key.example
    return [f"# {key.help}", f"# {key.short_name} = {json.dumps(shown)}"]


def _config(top: "_TableReader") -> Config:
    return Config(
        default_lang=top.read(_DEFAULT_LANG),
        open_on_start=top.read(_OPEN_ON_START),
        progress_db=top.read(_PROGRESS_DB),
        next=_next_settings(top.table("next")),
        time_limit=_time_limit_settings(top.table("time_limit")),
        hang_guard=_hang_guard_settings(top.table("hang_guard")),
        bench=_bench_settings(top.table("bench")),
        schedule=_schedule_settings(top.table("schedule")),
        done=_done_settings(top.table("done")),
        study_guides=_study_guide_settings(top.table("study_guides")),
    )


def _next_settings(table: "_TableReader") -> NextSettings:
    return NextSettings(tracks=table.read(_TRACKS))


def _time_limit_settings(table: "_TableReader") -> TimeLimitSettings:
    return TimeLimitSettings(
        enabled=table.read(_TIME_LIMIT_ENABLED),
        value=table.read(_TIME_LIMIT_VALUE),
        floor_ms=table.read(_TIME_LIMIT_FLOOR),
    )


def _hang_guard_settings(table: "_TableReader") -> HangGuardSettings:
    return HangGuardSettings(ms=table.read(_HANG_GUARD_MS))


def _bench_settings(table: "_TableReader") -> BenchSettings:
    return BenchSettings(reps=table.read(_BENCH_REPS), memory=table.read(_BENCH_MEMORY))


def _schedule_settings(table: "_TableReader") -> ScheduleSettings:
    settings = ScheduleSettings(
        penalize_suboptimal=table.read(_PENALIZE_SUBOPTIMAL),
        max_interval_days=table.read(_MAX_INTERVAL),
        intervals=ReviewIntervals(
            again=table.read(_AGAIN_INTERVAL),
            hard_first=table.read(_HARD_FIRST_INTERVAL),
            ok_first=table.read(_OK_FIRST_INTERVAL),
            ok_second=table.read(_OK_SECOND_INTERVAL),
            easy_first=table.read(_EASY_FIRST_INTERVAL),
            easy_second=table.read(_EASY_SECOND_INTERVAL),
        ),
        mastered_interval_days=table.read(_MASTERED_INTERVAL),
    )
    _require_mastered_reachable(table, settings)
    return settings


def _require_mastered_reachable(table: "_TableReader", settings: ScheduleSettings) -> None:
    """No interval passes `max_interval_days`, so a higher threshold could never be reached. Only
    a threshold set on purpose is refused: a config from before the key, with a low maximum, keeps
    loading as it did."""
    mastered, maximum = settings.mastered_interval_days, settings.max_interval_days
    if table.holds(_MASTERED_INTERVAL) and mastered > maximum:
        table.report(
            _MASTERED_INTERVAL,
            f"{mastered} is above schedule.max_interval_days ({maximum}), "
            "so no problem could ever be mastered",
        )


def _done_settings(table: "_TableReader") -> DoneSettings:
    return DoneSettings(auto_commit=table.read(_AUTO_COMMIT))


def _study_guide_settings(table: "_TableReader") -> StudyGuideSettings:
    return StudyGuideSettings(root=table.read(_STUDY_GUIDES_ROOT))


class _TableReader:
    """Typed reads from one TOML table that record issues instead of stopping at the first."""

    def __init__(self, values: _Table, prefix: str, issues: list[str]) -> None:
        self._values = values
        self._prefix = prefix
        self._issues = issues
        self._known_keys: set[str] = set()
        self._children: list[_TableReader] = []

    def read[T](self, key: "_Key[T]") -> T:
        name = key.description.short_name
        self._known_keys.add(name)
        if name not in self._values:
            return key.default
        try:
            return key.convert(self._values[name])
        except ValueError as error:
            self.report(key, str(error))
            return key.default

    def table(self, key: str) -> Self:
        self._known_keys.add(key)
        values = self._values.get(key, {})
        if not isinstance(values, Mapping):
            self._issues.append(f"{self._prefix}{key}: expected a table")
            values = {}
        child = type(self)(cast(_Table, values), f"{self._prefix}{key}.", self._issues)
        self._children.append(child)
        return child

    def holds(self, key: "_Key[Any]") -> bool:
        return key.description.short_name in self._values

    def report(self, key: "_Key[Any]", issue: str) -> None:
        self._issues.append(f"{key.description.name}: {issue}")

    def report_unknown_keys(self) -> None:
        for key in sorted(self._values.keys() - self._known_keys):
            self._issues.append(f"{self._prefix}{key}: unknown key")
        for child in self._children:
            child.report_unknown_keys()

    def read_key_names(self) -> frozenset[str]:
        """The dotted names of the keys read, without the tables they are in."""
        tables = {child._prefix.removesuffix(".") for child in self._children}
        own = {f"{self._prefix}{key}" for key in self._known_keys} - tables
        return frozenset(own).union(*(child.read_key_names() for child in self._children))


def _boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError("expected true or false")


def _positive_int(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    raise ValueError("expected a positive integer")


def _string(value: object) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError("expected a non-empty string")


def _directory(value: object) -> str:
    """An absolute path or a `~/`-relative one; the caller expands `~` against the home."""
    if isinstance(value, str) and (Path(value).is_absolute() or value.startswith(HOME_PREFIX)):
        return value
    raise ValueError(f'expected an absolute path or one starting with "{HOME_PREFIX}"')


def _language(value: object) -> Language:
    if isinstance(value, str) and value in Language:
        return Language(value)
    raise ValueError(f"expected one of {', '.join(Language)}")


def _tracks(value: object) -> tuple[Track, ...]:
    if not isinstance(value, list):
        raise ValueError("expected a list of track ids")
    return tuple(_track(item) for item in cast(list[object], value))


def _track(value: object) -> Track:
    if isinstance(value, str) and value in Track:
        return Track(value)
    raise ValueError(f'unknown track "{value}"')


def _time_limit(value: object) -> TimeLimit:
    if not isinstance(value, str):
        raise ValueError('expected a string such as "5x" or "1500ms"')
    return parse_time_limit(value)


@dataclass(frozen=True, slots=True)
class _Key[T]:
    """One key of the file: how the parser reads it and what the Settings view says of it."""

    description: ConfigKey
    default: T
    convert: Callable[[object], T]


_DEFAULTS = Config()
_NEXT_COMMAND = "at the next command"
_NEXT_RUN = "at the next run, in the terminal or the page"
_NEXT_REVIEW = "for reviews scheduled from now on; dates already set do not move"
_DEFAULT_LANG = _Key(
    ConfigKey(
        "default_lang",
        KeyKind.CHOICE,
        _DEFAULTS.default_lang.value,
        "The language cstudy start uses when you name none.",
        f"{_NEXT_COMMAND}; an open page after a reload",
        tuple(Language),
    ),
    _DEFAULTS.default_lang,
    _language,
)
_OPEN_ON_START = _Key(
    ConfigKey(
        "open_on_start",
        KeyKind.BOOLEAN,
        _DEFAULTS.open_on_start,
        "Open $VISUAL or $EDITOR on cstudy start. The page never opens an editor.",
        _NEXT_COMMAND,
    ),
    _DEFAULTS.open_on_start,
    _boolean,
)
_PROGRESS_DB = _Key(
    ConfigKey(
        "progress_db",
        KeyKind.TEXT,
        _DEFAULTS.progress_db,
        "The progress database, relative to the workspace root. Changing this path does not move "
        "your data: it stays in the old file, and cstudy uses the file at the new path, or starts "
        "an empty one there.",
        f"{_NEXT_COMMAND}; restart cstudy serve, whose live updates watch the old file until then",
    ),
    _DEFAULTS.progress_db,
    _string,
)
_TRACKS = _Key(
    ConfigKey(
        "next.tracks",
        KeyKind.CHOICES,
        [track.value for track in _DEFAULTS.next.tracks],
        "The tracks cstudy next and cstudy mock pick from when you name none.",
        _NEXT_COMMAND,
        tuple(Track),
    ),
    _DEFAULTS.next.tracks,
    _tracks,
)
_TIME_LIMIT_ENABLED = _Key(
    ConfigKey(
        "time_limit.enabled",
        KeyKind.BOOLEAN,
        _DEFAULTS.time_limit.enabled,
        "Apply time limits to runs without --time-limit.",
        _NEXT_RUN,
    ),
    _DEFAULTS.time_limit.enabled,
    _boolean,
)
_TIME_LIMIT_VALUE = _Key(
    ConfigKey(
        "time_limit.value",
        KeyKind.TEXT,
        None,
        "The limit, such as 5x or 1500ms. Unset, each problem's suggested limit applies.",
        _NEXT_RUN,
        example="5x",
    ),
    _DEFAULTS.time_limit.value,
    _time_limit,
)
_TIME_LIMIT_FLOOR = _Key(
    ConfigKey(
        "time_limit.floor_ms",
        KeyKind.INTEGER,
        _DEFAULTS.time_limit.floor_ms,
        "No calibrated limit goes below this many milliseconds.",
        _NEXT_RUN,
    ),
    _DEFAULTS.time_limit.floor_ms,
    _positive_int,
)
_HANG_GUARD_MS = _Key(
    ConfigKey(
        "hang_guard.ms",
        KeyKind.INTEGER,
        None,
        "Stop a case that runs this many milliseconds. Unset, the case's or problem's value "
        "applies, then 10000.",
        _NEXT_RUN,
        example=10000,
    ),
    _DEFAULTS.hang_guard.ms,
    _positive_int,
)
_BENCH_REPS = _Key(
    ConfigKey(
        "bench.reps",
        KeyKind.INTEGER,
        _DEFAULTS.bench.reps,
        "How many times cstudy bench repeats each size.",
        "at the next bench",
    ),
    _DEFAULTS.bench.reps,
    _positive_int,
)
_BENCH_MEMORY = _Key(
    ConfigKey(
        "bench.memory",
        KeyKind.BOOLEAN,
        _DEFAULTS.bench.memory,
        "Measure memory as well as time in cstudy bench.",
        "at the next bench",
    ),
    _DEFAULTS.bench.memory,
    _boolean,
)
_PENALIZE_SUBOPTIMAL = _Key(
    ConfigKey(
        "schedule.penalize_suboptimal",
        KeyKind.BOOLEAN,
        _DEFAULTS.schedule.penalize_suboptimal,
        "A suboptimal bench verdict caps the review grade at hard.",
        "at the next cstudy done",
    ),
    _DEFAULTS.schedule.penalize_suboptimal,
    _boolean,
)


def _interval_key(name: str, default: int, what: str) -> _Key[int]:
    description = ConfigKey(f"schedule.{name}", KeyKind.INTEGER, default, what, _NEXT_REVIEW)
    return _Key(description, default, _positive_int)


_INTERVALS = _DEFAULTS.schedule.intervals
_MAX_INTERVAL = _interval_key(
    "max_interval_days",
    _DEFAULTS.schedule.max_interval_days,
    "No review is scheduled further away than this many days.",
)
_AGAIN_INTERVAL = _interval_key(
    "again_interval_days", _INTERVALS.again, "Days to the next review after an again."
)
_HARD_FIRST_INTERVAL = _interval_key(
    "hard_first_interval_days", _INTERVALS.hard_first, "Days after a first review rated hard."
)
_OK_FIRST_INTERVAL = _interval_key(
    "ok_first_interval_days", _INTERVALS.ok_first, "Days after a first review rated ok."
)
_OK_SECOND_INTERVAL = _interval_key(
    "ok_second_interval_days", _INTERVALS.ok_second, "Days after a second review rated ok."
)
_EASY_FIRST_INTERVAL = _interval_key(
    "easy_first_interval_days", _INTERVALS.easy_first, "Days after a first review rated easy."
)
_EASY_SECOND_INTERVAL = _interval_key(
    "easy_second_interval_days", _INTERVALS.easy_second, "Days after a second review rated easy."
)
_MASTERED_INTERVAL = _Key(
    ConfigKey(
        "schedule.mastered_interval_days",
        KeyKind.INTEGER,
        _DEFAULTS.schedule.mastered_interval_days,
        "A problem counts as mastered from this interval on, with a grade of ok or easy.",
        "at once, for every problem: it is read each time a status shows",
    ),
    _DEFAULTS.schedule.mastered_interval_days,
    _positive_int,
)
_AUTO_COMMIT = _Key(
    ConfigKey(
        "done.auto_commit",
        KeyKind.BOOLEAN,
        _DEFAULTS.done.auto_commit,
        "Reserved: it does nothing yet.",
        "never: it is reserved",
        reserved=True,
    ),
    _DEFAULTS.done.auto_commit,
    _boolean,
)
_STUDY_GUIDES_ROOT = _Key(
    ConfigKey(
        "study_guides.root",
        KeyKind.TEXT,
        None,
        "Where your study guides live, absolute or starting with ~/. Unset, no guide is linked.",
        _NEXT_COMMAND,
        example="~/study-guides",
    ),
    _DEFAULTS.study_guides.root,
    _directory,
)
_KEYS: tuple[_Key[Any], ...] = (
    _DEFAULT_LANG,
    _OPEN_ON_START,
    _PROGRESS_DB,
    _TRACKS,
    _TIME_LIMIT_ENABLED,
    _TIME_LIMIT_VALUE,
    _TIME_LIMIT_FLOOR,
    _HANG_GUARD_MS,
    _BENCH_REPS,
    _BENCH_MEMORY,
    _PENALIZE_SUBOPTIMAL,
    _MAX_INTERVAL,
    _AGAIN_INTERVAL,
    _HARD_FIRST_INTERVAL,
    _OK_FIRST_INTERVAL,
    _OK_SECOND_INTERVAL,
    _EASY_FIRST_INTERVAL,
    _EASY_SECOND_INTERVAL,
    _MASTERED_INTERVAL,
    _AUTO_COMMIT,
    _STUDY_GUIDES_ROOT,
)
CONFIG_KEYS = tuple(key.description for key in _KEYS)
"""Every key, in the order of the file: what the Settings view draws and `cstudy config edit`'s
template lists. A test holds it equal to what the parser reads."""
