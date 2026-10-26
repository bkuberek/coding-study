from coding_study.domain.config import Config, HangGuardSettings, TimeLimitSettings
from coding_study.domain.precedence import (
    DEFAULT_HANG_GUARD_MS,
    first_set,
    resolve_hang_guard_ms,
    resolve_language,
    resolve_time_limit,
    time_limits_enabled,
)
from coding_study.domain.problem import Language
from coding_study.domain.time_limits import (
    DEFAULT_TIME_LIMIT,
    AbsoluteTimeLimit,
    FactorTimeLimit,
)

CONFIG_LIMIT = FactorTimeLimit(3)
META_LIMIT = AbsoluteTimeLimit(1500)
FLAG_LIMIT = FactorTimeLimit(10)


def config_with_time_limit(*, enabled: bool = False, value=None) -> Config:
    return Config(time_limit=TimeLimitSettings(enabled=enabled, value=value))


def test_first_set_returns_first_candidate_that_is_not_none():
    assert first_set(None, 0, 5, default=9) == 0


def test_first_set_falls_back_to_default():
    assert first_set(None, None, default=9) == 9


def test_first_set_keeps_false_as_a_set_value():
    assert first_set(False, True, default=True) is False


def test_language_flag_beats_config():
    assert resolve_language(Language.KOTLIN, Config(default_lang=Language.JAVA)) == Language.KOTLIN


def test_language_falls_back_to_config():
    assert resolve_language(None, Config(default_lang=Language.JAVA)) == Language.JAVA


def test_language_built_in_default_is_python():
    assert resolve_language(None, Config()) == Language.PYTHON


def test_time_limits_are_off_by_default():
    assert time_limits_enabled(None, Config()) is False


def test_config_enables_time_limits():
    assert time_limits_enabled(None, config_with_time_limit(enabled=True)) is True


def test_no_time_limit_flag_beats_config():
    assert time_limits_enabled(False, config_with_time_limit(enabled=True)) is False


def test_time_limit_flag_beats_config():
    assert time_limits_enabled(True, Config()) is True


def test_time_limit_value_flag_beats_config_and_meta():
    config = config_with_time_limit(value=CONFIG_LIMIT)
    assert resolve_time_limit(FLAG_LIMIT, config, META_LIMIT) == FLAG_LIMIT


def test_time_limit_value_config_beats_meta():
    config = config_with_time_limit(value=CONFIG_LIMIT)
    assert resolve_time_limit(None, config, META_LIMIT) == CONFIG_LIMIT


def test_time_limit_value_meta_beats_built_in_default():
    assert resolve_time_limit(None, Config(), META_LIMIT) == META_LIMIT


def test_time_limit_value_built_in_default_is_five_times():
    assert resolve_time_limit(None, Config(), None) == DEFAULT_TIME_LIMIT == FactorTimeLimit(5)


def test_hang_guard_config_beats_case_and_meta():
    config = Config(hang_guard=HangGuardSettings(ms=2000))
    assert resolve_hang_guard_ms(config, 3000, 4000) == 2000


def test_hang_guard_case_beats_meta():
    assert resolve_hang_guard_ms(Config(), 3000, 4000) == 3000


def test_hang_guard_meta_beats_built_in_default():
    assert resolve_hang_guard_ms(Config(), None, 4000) == 4000


def test_hang_guard_built_in_default_is_ten_seconds():
    assert resolve_hang_guard_ms(Config(), None, None) == DEFAULT_HANG_GUARD_MS == 10_000
