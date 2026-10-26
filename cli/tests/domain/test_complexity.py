import math

import pytest

from coding_study.domain.complexity import (
    DRIFT_TOLERANCE,
    MemoryBand,
    Point,
    TimeBand,
    band_of_class,
    class_drift,
    classify_memory,
    classify_time,
    log_log_fit,
    memory_band_of_slope,
    semi_log_fit,
    time_band_of_slope,
)
from coding_study.domain.problem import ComplexityClass

SIZES = (100, 1000, 10_000, 100_000)
MEASURED_LINEAR_ON_A_NARROW_LADDER = [
    Point(1000, 472_332),
    Point(2000, 615_175),
    Point(5000, 1_667_733),
    Point(10_000, 5_511_625),
]
"""A linear reference whose local slopes rise on a one-decade ladder (Python, under load)."""


def growth(exponent: float, scale: float = 10.0, sizes: tuple[int, ...] = SIZES) -> list[Point]:
    return [Point(size, scale * size**exponent) for size in sizes]


def test_a_power_law_fits_its_exponent():
    assert log_log_fit(growth(2.0)).slope == pytest.approx(2.0)


def test_a_power_law_fits_perfectly():
    assert log_log_fit(growth(1.0)).r2 == pytest.approx(1.0)


def test_a_flat_series_has_slope_zero():
    assert log_log_fit([Point(size, 5.0) for size in SIZES]).slope == pytest.approx(0.0)


def test_a_flat_series_counts_as_a_perfect_fit():
    assert log_log_fit([Point(size, 5.0) for size in SIZES]).r2 == 1.0


def test_noise_lowers_r_squared():
    noisy = [
        Point(size, size * factor) for size, factor in zip(SIZES, (1.0, 3.0, 0.5, 2.0), strict=True)
    ]
    assert log_log_fit(noisy).r2 < 0.98


def test_a_fit_needs_two_sizes():
    with pytest.raises(ValueError, match="two sizes"):
        log_log_fit([Point(100, 1.0)])


def test_semi_log_fit_measures_growth_per_unit_of_n():
    points = [Point(n, 2.0**n) for n in (10, 15, 20, 25)]
    assert semi_log_fit(points).slope == pytest.approx(math.log(2))


@pytest.mark.parametrize(
    ("slope", "band"),
    [
        (-0.2, TimeBand.A),
        (0.0, TimeBand.A),
        (0.3, TimeBand.A),
        (0.74, TimeBand.A),
        (0.75, TimeBand.C),
        (1.0, TimeBand.C),
        (1.34, TimeBand.C),
        (1.35, TimeBand.D),
        (1.74, TimeBand.D),
        (1.75, TimeBand.E),
        (2.34, TimeBand.E),
        (2.35, TimeBand.F),
        (2.75, TimeBand.G),
        (3.39, TimeBand.G),
        (3.4, TimeBand.X),
        (6.0, TimeBand.X),
    ],
)
def test_slopes_map_to_bands(slope, band):
    assert time_band_of_slope(slope) is band


def test_bands_are_ordered_by_growth():
    assert TimeBand.C.worse_than(TimeBand.A)


def test_exponential_is_the_worst_band():
    assert all(TimeBand.X.worse_than(band) for band in TimeBand if band is not TimeBand.X)


def test_a_band_is_not_worse_than_itself():
    assert not TimeBand.E.worse_than(TimeBand.E)


@pytest.mark.parametrize(
    ("declared", "band"),
    [
        (ComplexityClass.CONSTANT, TimeBand.A),
        (ComplexityClass.LOGARITHMIC, TimeBand.A),
        (ComplexityClass.SQUARE_ROOT, TimeBand.A),
        (ComplexityClass.LINEAR, TimeBand.C),
        (ComplexityClass.LINEARITHMIC, TimeBand.C),
        (ComplexityClass.QUADRATIC, TimeBand.E),
        (ComplexityClass.QUADRATIC_LOGARITHMIC, TimeBand.E),
        (ComplexityClass.CUBIC, TimeBand.G),
        (ComplexityClass.EXPONENTIAL, TimeBand.X),
        (ComplexityClass.FACTORIAL, TimeBand.X),
    ],
)
def test_declared_classes_belong_to_bands(declared, band):
    assert band_of_class(declared) is band


def test_a_logarithmic_series_behind_a_cache_cliff_stays_sublinear():
    points = [Point(100, 11.0), Point(1000, 94.0), Point(10_000, 120.0)]
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is TimeBand.A


def test_bands_between_classes_hold_no_declared_class():
    assert TimeBand.D.classes == ()


def test_time_needs_three_sizes():
    assert classify_time(growth(1.0, sizes=(100, 1000))) is None


def test_time_growth_reports_its_band():
    classified = classify_time(growth(2.0))
    assert classified is not None
    assert classified.band is TimeBand.E


def test_time_growth_keeps_the_fitted_sizes():
    classified = classify_time(growth(1.0))
    assert classified is not None
    assert classified.sizes == SIZES


def test_an_n_log_n_series_lands_in_the_linear_band():
    points = [Point(size, size * math.log(size)) for size in SIZES]
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is TimeBand.C


def test_doubling_per_step_is_exponential():
    points = [Point(n, 1000.0 * 2.0**n) for n in (10, 14, 18, 22)]
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is TimeBand.X


def test_a_steep_polynomial_is_not_exponential():
    classified = classify_time(growth(3.0))
    assert classified is not None
    assert classified.band is TimeBand.G


def test_factorial_growth_is_exponential():
    points = [Point(n, 50.0 * math.factorial(n) * n) for n in (4, 5, 6)]
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is TimeBand.X


def test_growth_steeper_than_any_polynomial_class_on_a_short_ladder_is_exponential():
    points = [Point(6, 65_479), Point(7, 303_734), Point(8, 1_208_492)]
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is TimeBand.X


def test_a_power_law_steeper_than_the_cubic_band_reads_as_exponential():
    classified = classify_time(growth(5.0))
    assert classified is not None
    assert classified.band is TimeBand.X


def test_steep_growth_that_slows_at_the_top_is_still_exponential():
    points = [Point(6, 2_000.0), Point(8, 12_000.0), Point(10, 24_000.0)]
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is TimeBand.X


def test_a_cubic_series_with_a_steep_last_step_is_not_exponential():
    points = [Point(100, 1e6), Point(200, 7.5e6), Point(500, 1.2e8), Point(1000, 1.36e9)]
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is TimeBand.G


def test_exponential_growth_behind_a_fixed_cost_is_exponential():
    points = [Point(n, 1000.0 + 50.0 * 4.0**n) for n in (2, 4, 6)]
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is TimeBand.X


@pytest.mark.parametrize(
    "points",
    [
        pytest.param(
            [Point(n, 200_000.0 + 20.0 * n) for n in (1000, 10_000, 50_000)],
            id="fixed cost plus linear",
        ),
        pytest.param(
            [Point(n, 1e6 + 0.5 * n * n) for n in (1000, 2000, 5000, 10_000)],
            id="fixed cost plus quadratic",
        ),
        pytest.param(MEASURED_LINEAR_ON_A_NARROW_LADDER, id="measured linear, narrow ladder"),
    ],
)
def test_rising_slopes_below_the_polynomial_ceiling_are_not_exponential(points):
    classified = classify_time(points)
    assert classified is not None
    assert classified.band is not TimeBand.X


@pytest.mark.parametrize(
    ("slope", "band"),
    [
        (0.0, MemoryBand.CONSTANT),
        (0.29, MemoryBand.CONSTANT),
        (0.3, MemoryBand.SUBLINEAR),
        (0.75, MemoryBand.LINEAR),
        (1.34, MemoryBand.LINEAR),
        (1.35, MemoryBand.SUPERLINEAR),
    ],
)
def test_memory_slopes_map_to_bands(slope, band):
    assert memory_band_of_slope(slope) is band


def test_memory_under_four_kib_counts_as_constant():
    classified = classify_memory([Point(size, 700.0 + size / 100) for size in SIZES])
    assert classified is not None
    assert classified.band is MemoryBand.CONSTANT


def test_memory_growing_with_n_is_linear():
    classified = classify_memory(growth(1.0, scale=70.0))
    assert classified is not None
    assert classified.band is MemoryBand.LINEAR


def test_memory_needs_three_sizes():
    assert classify_memory(growth(1.0, sizes=(100, 1000))) is None


def test_memory_bands_are_ordered():
    assert MemoryBand.LINEAR.worse_than(MemoryBand.CONSTANT)


def drift(points: list[Point], declared: ComplexityClass = ComplexityClass.LINEAR) -> float:
    value = class_drift(points, declared)
    assert value is not None
    return value


def test_a_series_of_its_own_class_does_not_drift():
    assert drift(growth(1.0)) == pytest.approx(1.0)


def test_a_fixed_cost_before_linear_growth_is_not_drift():
    points = [Point(size, 10_000.0 + 10.0 * size) for size in SIZES]
    assert drift(points) == pytest.approx(1.0)


def test_a_fixed_cost_before_n_log_n_growth_is_not_drift():
    points = [Point(size, 20_000.0 + 5.0 * size * math.log(size)) for size in SIZES]
    assert drift(points, ComplexityClass.LINEARITHMIC) == pytest.approx(1.0)


def test_quadratic_growth_drifts_against_the_linear_class():
    assert drift(growth(2.0)) == pytest.approx(1000.0)


def test_linear_growth_drifts_against_the_quadratic_class():
    assert drift(growth(1.0), ComplexityClass.QUADRATIC) > DRIFT_TOLERANCE


def test_n_log_n_growth_stays_within_the_tolerance_of_the_linear_class():
    points = [Point(size, size * math.log(size)) for size in SIZES]
    assert drift(points) < DRIFT_TOLERANCE


def test_a_fixed_cost_cannot_explain_a_series_that_never_grows():
    points = [Point(size, 5000.0) for size in SIZES]
    assert drift(points) > DRIFT_TOLERANCE


def test_cache_drift_of_a_linear_series_stays_within_the_tolerance():
    per_element = (7.8, 6.3, 12.4, 21.1)
    points = [Point(size, size * cost) for size, cost in zip(SIZES, per_element, strict=True)]
    assert drift(points) < DRIFT_TOLERANCE


def test_noise_on_a_measured_linear_reference_stays_within_the_tolerance():
    assert drift(MEASURED_LINEAR_ON_A_NARROW_LADDER) < DRIFT_TOLERANCE


def test_quadratic_growth_on_a_narrow_ladder_exceeds_the_tolerance():
    assert drift(growth(2.0, sizes=(1000, 2000, 5000, 10_000))) > DRIFT_TOLERANCE


@pytest.mark.parametrize("declared", [ComplexityClass.EXPONENTIAL, ComplexityClass.FACTORIAL])
def test_exponential_classes_have_no_drift(declared):
    assert class_drift(growth(1.0), declared) is None
