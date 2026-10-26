"""User configuration (docs/specs/cli.md#configuration); every default lives here."""

from dataclasses import dataclass

from coding_study.domain.problem import Language, Track
from coding_study.domain.time_limits import TimeLimit

DEFAULT_PROGRESS_DB = "progress.db"
DEFAULT_TIME_LIMIT_FLOOR_MS = 100
DEFAULT_BENCH_REPS = 7
DEFAULT_MAX_INTERVAL_DAYS = 180


@dataclass(frozen=True, slots=True)
class NextSettings:
    tracks: tuple[Track, ...] = (Track.DSA,)


@dataclass(frozen=True, slots=True)
class TimeLimitSettings:
    enabled: bool = False
    value: TimeLimit | None = None
    floor_ms: int = DEFAULT_TIME_LIMIT_FLOOR_MS


@dataclass(frozen=True, slots=True)
class HangGuardSettings:
    ms: int | None = None


@dataclass(frozen=True, slots=True)
class BenchSettings:
    reps: int = DEFAULT_BENCH_REPS
    memory: bool = True


@dataclass(frozen=True, slots=True)
class ScheduleSettings:
    penalize_suboptimal: bool = True
    max_interval_days: int = DEFAULT_MAX_INTERVAL_DAYS


@dataclass(frozen=True, slots=True)
class DoneSettings:
    auto_commit: bool = False


@dataclass(frozen=True, slots=True)
class StudyGuideSettings:
    root: str | None = None
    """The directory item `references.study_guides` paths are relative to: absolute or
    `~/`-relative. Unset, `cstudy start` and `cstudy show` link no study guide."""


@dataclass(frozen=True, slots=True)
class Config:
    default_lang: Language = Language.PYTHON
    open_on_start: bool = True
    progress_db: str = DEFAULT_PROGRESS_DB
    next: NextSettings = NextSettings()
    time_limit: TimeLimitSettings = TimeLimitSettings()
    hang_guard: HangGuardSettings = HangGuardSettings()
    bench: BenchSettings = BenchSettings()
    schedule: ScheduleSettings = ScheduleSettings()
    done: DoneSettings = DoneSettings()
    study_guides: StudyGuideSettings = StudyGuideSettings()
