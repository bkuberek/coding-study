"""The user config file (docs/specs/cli.md#configuration).

Location precedence: `CSTUDY_CONFIG`, then `$XDG_CONFIG_HOME/coding-study/config.toml`, then
`~/.config/coding-study/config.toml`. Every key is optional; omitted keys keep the defaults
defined in `coding_study.domain.config`.
"""

import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Self, cast

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
from coding_study.domain.errors import ConfigError
from coding_study.domain.problem import Language, Track
from coding_study.domain.time_limits import TimeLimit, parse_time_limit

CONFIG_PATH_VARIABLE = "CSTUDY_CONFIG"
XDG_CONFIG_HOME_VARIABLE = "XDG_CONFIG_HOME"
CONFIG_FILE = Path("coding-study") / "config.toml"

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
    issues: list[str] = []
    top = _TableReader(values, "", issues)
    defaults = Config()
    config = Config(
        default_lang=top.read("default_lang", defaults.default_lang, _language),
        open_on_start=top.read("open_on_start", defaults.open_on_start, _boolean),
        progress_db=top.read("progress_db", defaults.progress_db, _string),
        next=_next_settings(top.table("next")),
        time_limit=_time_limit_settings(top.table("time_limit")),
        hang_guard=_hang_guard_settings(top.table("hang_guard")),
        bench=_bench_settings(top.table("bench")),
        schedule=_schedule_settings(top.table("schedule")),
        done=_done_settings(top.table("done")),
        study_guides=_study_guide_settings(top.table("study_guides")),
    )
    top.report_unknown_keys()
    if issues:
        raise ConfigError(source, issues)
    return config


def _next_settings(table: "_TableReader") -> NextSettings:
    return NextSettings(tracks=table.read("tracks", NextSettings().tracks, _tracks))


def _time_limit_settings(table: "_TableReader") -> TimeLimitSettings:
    defaults = TimeLimitSettings()
    return TimeLimitSettings(
        enabled=table.read("enabled", defaults.enabled, _boolean),
        value=table.read("value", defaults.value, _time_limit),
        floor_ms=table.read("floor_ms", defaults.floor_ms, _positive_int),
    )


def _hang_guard_settings(table: "_TableReader") -> HangGuardSettings:
    return HangGuardSettings(ms=table.read("ms", HangGuardSettings().ms, _positive_int))


def _bench_settings(table: "_TableReader") -> BenchSettings:
    defaults = BenchSettings()
    return BenchSettings(
        reps=table.read("reps", defaults.reps, _positive_int),
        memory=table.read("memory", defaults.memory, _boolean),
    )


def _schedule_settings(table: "_TableReader") -> ScheduleSettings:
    defaults = ScheduleSettings()
    return ScheduleSettings(
        penalize_suboptimal=table.read(
            "penalize_suboptimal", defaults.penalize_suboptimal, _boolean
        ),
        max_interval_days=table.read(
            "max_interval_days", defaults.max_interval_days, _positive_int
        ),
    )


def _done_settings(table: "_TableReader") -> DoneSettings:
    return DoneSettings(auto_commit=table.read("auto_commit", DoneSettings().auto_commit, _boolean))


def _study_guide_settings(table: "_TableReader") -> StudyGuideSettings:
    return StudyGuideSettings(root=table.read("root", StudyGuideSettings().root, _directory))


class _TableReader:
    """Typed reads from one TOML table that record issues instead of stopping at the first."""

    def __init__(self, values: _Table, prefix: str, issues: list[str]) -> None:
        self._values = values
        self._prefix = prefix
        self._issues = issues
        self._known_keys: set[str] = set()
        self._children: list[_TableReader] = []

    def read[T](self, key: str, default: T, convert: Callable[[object], T]) -> T:
        self._known_keys.add(key)
        if key not in self._values:
            return default
        try:
            return convert(self._values[key])
        except ValueError as error:
            self._issues.append(f"{self._prefix}{key}: {error}")
            return default

    def table(self, key: str) -> Self:
        self._known_keys.add(key)
        values = self._values.get(key, {})
        if not isinstance(values, Mapping):
            self._issues.append(f"{self._prefix}{key}: expected a table")
            values = {}
        child = type(self)(cast(_Table, values), f"{self._prefix}{key}.", self._issues)
        self._children.append(child)
        return child

    def report_unknown_keys(self) -> None:
        for key in sorted(self._values.keys() - self._known_keys):
            self._issues.append(f"{self._prefix}{key}: unknown key")
        for child in self._children:
            child.report_unknown_keys()


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
