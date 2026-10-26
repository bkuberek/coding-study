import pytest

from coding_study.domain.bench_runs import (
    BenchSample,
    MemoryMeasurement,
    SizeMeasurements,
    TargetReport,
)
from coding_study.domain.bench_stats import (
    SizeStatus,
    analyze,
    duration_text,
    size_text,
    summarize,
)
from coding_study.domain.runs import Raised, UserError


def samples(*per_call_ns: int, calls: int = 1) -> tuple[BenchSample, ...]:
    return tuple(
        BenchSample(rep, value * calls, value * calls // 2, calls)
        for rep, value in enumerate(per_call_ns, start=1)
    )


def stats_of(*sizes: SizeMeasurements):
    return summarize(TargetReport("user", sizes)).sizes


def test_the_median_is_per_call():
    (stats,) = stats_of(SizeMeasurements(10, samples(100, 300, 200, calls=4)))
    assert stats.median_ns == 200


def test_spread_is_the_median_absolute_deviation_over_the_median():
    (stats,) = stats_of(SizeMeasurements(10, samples(90, 100, 110, 100, 200)))
    assert stats.spread == pytest.approx(0.1)


def test_cpu_time_is_the_median_per_call():
    (stats,) = stats_of(SizeMeasurements(10, samples(100, 200, 300, calls=2)))
    assert stats.cpu_ns == 100


def test_a_size_with_samples_is_completed():
    (stats,) = stats_of(SizeMeasurements(10, samples(100)))
    assert stats.status is SizeStatus.COMPLETED


def test_a_call_over_the_budget_marks_the_size():
    (stats,) = stats_of(SizeMeasurements(10, samples(100), exceeded_ns=5_000))
    assert (stats.status, stats.exceeded_ns) == (SizeStatus.BUDGET_EXCEEDED, 5_000)


def test_a_failure_marks_the_size():
    failure = Raised(UserError("ValueError", "x"), 0)
    (stats,) = stats_of(SizeMeasurements(10, failure=failure))
    assert stats.status is SizeStatus.FAILED


def test_a_size_without_samples_was_not_run():
    (stats,) = stats_of(SizeMeasurements(10))
    assert stats.status is SizeStatus.NOT_RUN


def test_memory_is_kept_with_its_metric():
    memory = MemoryMeasurement("tracemalloc_peak", 4096)
    (stats,) = stats_of(SizeMeasurements(10, samples(100), memory=memory))
    assert (stats.memory_bytes, stats.memory_metric) == (4096, "tracemalloc_peak")


def test_a_size_is_usable_when_its_samples_last_fifty_microseconds():
    (stats,) = stats_of(SizeMeasurements(10, samples(10_000, calls=5)))
    assert stats.usable


def test_a_size_with_shorter_samples_is_not_usable():
    (stats,) = stats_of(SizeMeasurements(10, samples(10_000, calls=4)))
    assert not stats.usable


def test_analysis_fits_only_usable_sizes():
    series = summarize(
        TargetReport(
            "user",
            (
                SizeMeasurements(10, samples(100)),
                SizeMeasurements(100, samples(100_000)),
                SizeMeasurements(1000, samples(1_000_000)),
                SizeMeasurements(10_000, samples(10_000_000)),
            ),
        )
    )
    time = analyze(series).time
    assert time is not None
    assert time.sizes == (100, 1000, 10_000)


def test_analysis_without_enough_sizes_has_no_time_growth():
    series = summarize(TargetReport("user", (SizeMeasurements(100, samples(100_000)),)))
    assert analyze(series).time is None


def test_the_largest_spread_counts_over_the_fitted_sizes_only():
    unusable = SizeMeasurements(10, samples(100, 200, 300))
    fitted = tuple(
        SizeMeasurements(size, samples(size * 900, size * 1000, size * 1100))
        for size in (100, 1000, 10_000)
    )
    analysis = analyze(summarize(TargetReport("user", (unusable, *fitted))))
    assert analysis.max_spread == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("size", "text"), [(100, "1e2"), (100_000, "1e5"), (1, "1"), (2500, "2500"), (30_000, "3e4")]
)
def test_sizes_print_as_powers_of_ten_when_round(size, text):
    assert size_text(size) == text


@pytest.mark.parametrize(
    ("nanoseconds", "text"),
    [
        (2_400, "2.4µs"),
        (9_940, "9.9µs"),
        (10_000, "0.01ms"),
        (1_234_000, "1.23ms"),
        (45_600_000, "45.6ms"),
        (987_000_000, "987ms"),
        (2_040_000_000, "2.04s"),
    ],
)
def test_durations_print_in_milliseconds_or_seconds(nanoseconds, text):
    assert duration_text(nanoseconds) == text
