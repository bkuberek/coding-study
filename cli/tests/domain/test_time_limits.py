import pytest

from coding_study.domain.time_limits import (
    AbsoluteTimeLimit,
    Calibration,
    CaseLimit,
    FactorTimeLimit,
    TimeLimits,
    fastest_calibration,
    parse_time_limit,
    per_case_medians,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5x", FactorTimeLimit(5)),
        ("5", FactorTimeLimit(5)),
        ("2.5x", FactorTimeLimit(2.5)),
        ("1500ms", AbsoluteTimeLimit(1500)),
        ("1.5s", AbsoluteTimeLimit(1500)),
        ("0.5ms", AbsoluteTimeLimit(0.5)),
    ],
)
def test_parses_factor_and_absolute_forms(text, expected):
    assert parse_time_limit(text) == expected


@pytest.mark.parametrize("text", ["", "x", "0", "0x", "0ms", "-5x", "5 x", "5min", "fast", ".5x"])
def test_rejects_malformed_or_non_positive_values(text):
    with pytest.raises(ValueError, match="invalid time limit"):
        parse_time_limit(text)


@pytest.mark.parametrize(
    ("limit", "text"),
    [
        (FactorTimeLimit(5), "5x"),
        (FactorTimeLimit(2.5), "2.5x"),
        (AbsoluteTimeLimit(1500), "1500ms"),
    ],
)
def test_renders_canonical_text(limit, text):
    assert str(limit) == text


MS = 1_000_000
HASH_MAP = Calibration("hash-map", {"ex1": 2 * MS, "g1": 40 * MS})


def factor_limits(factor: float = 5, floor_ms: int = 100) -> TimeLimits:
    return TimeLimits(FactorTimeLimit(factor), floor_ms, HASH_MAP)


def test_factor_limit_scales_the_calibrated_case_time():
    assert factor_limits().for_case("g1") == CaseLimit(200, "5x hash-map, calibrated")


def test_factor_limit_never_drops_below_the_floor():
    assert factor_limits().for_case("ex1") == CaseLimit(100, "floor")


def test_factor_limit_at_exactly_the_floor_is_the_calibrated_limit():
    assert factor_limits(floor_ms=200).for_case("g1") == CaseLimit(200, "5x hash-map, calibrated")


def test_factor_limit_without_a_calibrated_time_for_the_case_is_none():
    assert factor_limits().for_case("h7") is None


def test_absolute_limit_is_the_same_for_every_case():
    limits = TimeLimits(AbsoluteTimeLimit(1500), 100)
    assert [limits.for_case(case) for case in ("ex1", "h7")] == [CaseLimit(1500, "")] * 2


def test_absolute_limit_ignores_the_floor():
    assert TimeLimits(AbsoluteTimeLimit(20), 100).for_case("ex1") == CaseLimit(20, "")


def test_per_case_medians_take_the_middle_run():
    runs = [{"a": 5, "b": 1}, {"a": 1, "b": 2}, {"a": 3, "b": 9}]
    assert per_case_medians(runs) == {"a": 3, "b": 2}


def test_per_case_medians_use_only_the_runs_that_measured_a_case():
    assert per_case_medians([{"a": 4}, {}, {"a": 6, "b": 7}]) == {"a": 5, "b": 7}


def test_fastest_calibration_has_the_smallest_total_over_shared_cases():
    medians = {"sort": {"a": 3, "b": 3}, "hash-map": {"a": 1, "b": 4}, "partial": {"a": 2}}
    assert fastest_calibration(medians) == Calibration("hash-map", {"a": 1, "b": 4})


def test_fastest_calibration_of_nothing_is_none():
    assert fastest_calibration({}) is None
