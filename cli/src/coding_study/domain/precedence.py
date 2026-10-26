"""Setting precedence: CLI flag, then config file, then meta.yaml, then built-in defaults.

Sources: docs/specs/cli.md#configuration, performance-analysis.md#precedence and
runners.md#hang-guard-and-restarts.
"""

from coding_study.domain.config import Config
from coding_study.domain.problem import Language
from coding_study.domain.time_limits import DEFAULT_TIME_LIMIT, TimeLimit

DEFAULT_HANG_GUARD_MS = 10_000


def first_set[T](*candidates: T | None, default: T) -> T:
    """The first candidate that is not None; falsy values such as False or 0 count as set."""
    return next((candidate for candidate in candidates if candidate is not None), default)


def resolve_language(flag: Language | None, config: Config) -> Language:
    return first_set(flag, default=config.default_lang)


def time_limits_enabled(flag: bool | None, config: Config) -> bool:
    """`--time-limit` enables and `--no-time-limit` disables; meta.yaml never turns limits on."""
    return first_set(flag, default=config.time_limit.enabled)


def resolve_time_limit(
    flag: TimeLimit | None, config: Config, suggested: TimeLimit | None
) -> TimeLimit:
    """`suggested` is the problem's `perf.time_limit`."""
    return first_set(flag, config.time_limit.value, suggested, default=DEFAULT_TIME_LIMIT)


def resolve_hang_guard_ms(config: Config, case_ms: int | None, meta_ms: int | None) -> int:
    return first_set(config.hang_guard.ms, case_ms, meta_ms, default=DEFAULT_HANG_GUARD_MS)
