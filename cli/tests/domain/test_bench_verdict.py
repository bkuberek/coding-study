from datetime import UTC, datetime

import pytest

from coding_study.domain.bench_stats import (
    SizeStats,
    SizeStatus,
    TargetAnalysis,
    TargetSeries,
    analyze,
)
from coding_study.domain.bench_verdict import (
    Conditions,
    Confidence,
    Ladder,
    LadderStatus,
    PastRun,
    Verdict,
    check_ladder,
    compare_history,
    judge,
)
from coding_study.domain.problem import Approach, ApproachRole, ComplexityClass

SIZES = (100, 1000, 10_000, 100_000)
CALLS = 1000
"""Enough calls per sample that every size is usable."""


def analysis(
    target_id: str,
    exponent: float = 1.0,
    *,
    scale: float = 10.0,
    sizes: tuple[int, ...] = SIZES,
    spread: float = 0.02,
    exceeded_at: int | None = None,
    memory_exponent: float | None = None,
    noise: tuple[float, ...] = (),
) -> TargetAnalysis:
    stats: list[SizeStats] = []
    for index, size in enumerate(sizes):
        if exceeded_at is not None and size >= exceeded_at:
            if size == exceeded_at:
                stats.append(SizeStats(size, SizeStatus.BUDGET_EXCEEDED, exceeded_ns=5 * 10**9))
            continue
        factor = noise[index] if noise else 1.0
        memory = None if memory_exponent is None else round(100 * size**memory_exponent)
        stats.append(
            SizeStats(
                size,
                SizeStatus.COMPLETED,
                median_ns=scale * size**exponent * factor,
                spread=spread,
                calls=CALLS,
                memory_bytes=memory,
                memory_metric="tracemalloc_peak" if memory is not None else None,
            )
        )
    return analyze(TargetSeries(target_id, tuple(stats)))


def ladder(*references: TargetAnalysis, optimal: tuple[str, ...] = ("hash-map",)) -> Ladder:
    return Ladder(references, frozenset(optimal))


OPTIMAL = analysis("hash-map", 1.0)
CLEAN = Conditions()


def time_verdict(user: TargetAnalysis, rungs: Ladder | None = None, conditions: Conditions = CLEAN):
    return judge(user, rungs or ladder(OPTIMAL), conditions).time


def test_fewer_than_three_usable_sizes_is_unknown():
    verdict = time_verdict(analysis("user", sizes=(100, 1000)))
    assert (verdict.verdict, verdict.message) == (
        Verdict.UNKNOWN,
        "not enough data: increase --sizes or reps",
    )


def test_an_unknown_verdict_has_low_confidence():
    assert time_verdict(analysis("user", sizes=(100, 1000))).confidence is Confidence.LOW


def test_no_optimal_reference_is_unknown():
    verdict = time_verdict(analysis("user"), ladder(OPTIMAL, optimal=()))
    assert (verdict.verdict, verdict.message) == (
        Verdict.UNKNOWN,
        "no optimal reference ran in this language",
    )


def test_exceeding_the_budget_where_optimal_completed_is_suboptimal():
    verdict = time_verdict(analysis("user", 2.0, exceeded_at=100_000))
    assert verdict.verdict is Verdict.SUBOPTIMAL


def test_the_budget_message_names_the_size_and_optimal_time():
    verdict = time_verdict(analysis("user", 2.0, exceeded_at=100_000))
    assert verdict.message == "exceeded budget at n=1e5 where optimal took 1.00ms"


def test_a_worse_band_is_suboptimal():
    verdict = time_verdict(analysis("user", 2.0))
    assert (verdict.verdict, verdict.message) == (
        Verdict.SUBOPTIMAL,
        "growth ~n^2 (slope 2.00), optimal is ~n|nlogn",
    )


def test_the_same_band_at_a_similar_speed_is_optimal():
    verdict = time_verdict(analysis("user", scale=11.0))
    assert (verdict.verdict, verdict.message) == (
        Verdict.OPTIMAL,
        "matches hash-map, 1.10x at n=1e5",
    )


def test_the_ratio_is_taken_at_the_largest_common_size():
    verdict = time_verdict(analysis("user", scale=11.0))
    assert (verdict.ratio, verdict.ratio_size) == (pytest.approx(1.1), 100_000)


def test_a_ratio_of_one_and_a_half_is_still_optimal():
    assert time_verdict(analysis("user", scale=15.0)).verdict is Verdict.OPTIMAL


def test_a_slower_constant_factor_is_near_optimal():
    verdict = time_verdict(analysis("user", scale=34.0))
    assert (verdict.verdict, verdict.message) == (
        Verdict.NEAR_OPTIMAL,
        "same growth, 3.4x slower constant factor",
    )


def test_a_ratio_growing_with_n_is_near_optimal():
    verdict = time_verdict(analysis("user", 1.15, scale=5.0))
    assert (verdict.verdict, verdict.message) == (
        Verdict.NEAR_OPTIMAL,
        "same band but ratio grows with n: likely an extra log factor",
    )


def test_the_trend_is_the_slope_of_the_log_ratio():
    assert time_verdict(analysis("user", 1.15, scale=5.0)).trend == pytest.approx(0.15)


def test_a_better_band_than_optimal_is_optimal():
    assert time_verdict(analysis("user", 0.0, scale=10**6)).verdict is Verdict.OPTIMAL


def test_a_better_band_than_optimal_warns_about_the_references():
    verdict = time_verdict(analysis("user", 0.0, scale=10**6))
    assert verdict.warning == "beats declared optimal: check references"


def test_the_fastest_optimal_reference_is_the_comparison():
    rungs = ladder(OPTIMAL, analysis("sorted", 1.0, scale=5.0), optimal=("hash-map", "sorted"))
    assert time_verdict(analysis("user"), rungs).reference_id == "sorted"


def test_a_brute_reference_is_never_the_comparison():
    rungs = ladder(analysis("brute-force", 2.0, scale=0.001), OPTIMAL)
    assert time_verdict(analysis("user"), rungs).reference_id == "hash-map"


def test_an_optimal_reference_with_too_few_sizes_gives_unknown():
    rungs = ladder(analysis("hash-map", sizes=(100, 1000)))
    verdict = time_verdict(analysis("user"), rungs)
    assert (verdict.verdict, verdict.message) == (
        Verdict.UNKNOWN,
        "optimal reference hash-map has too few usable sizes",
    )


def test_clean_fits_over_four_sizes_give_high_confidence():
    assert time_verdict(analysis("user")).confidence is Confidence.HIGH


def test_three_fitted_sizes_give_medium_confidence():
    verdict = time_verdict(analysis("user", 2.0, exceeded_at=100_000))
    assert verdict.confidence is Confidence.MEDIUM


def test_spread_over_ten_percent_gives_medium_confidence():
    assert time_verdict(analysis("user", spread=0.15)).confidence is Confidence.MEDIUM


def test_spread_over_a_quarter_gives_low_confidence():
    assert time_verdict(analysis("user", spread=0.3)).confidence is Confidence.LOW


def test_only_the_users_spread_counts():
    noisy_reference = ladder(analysis("hash-map", spread=0.3))
    assert time_verdict(analysis("user"), noisy_reference).confidence is Confidence.HIGH


def test_a_loose_fit_lowers_confidence():
    loose = analysis("user", noise=(1.0, 2.0, 0.6, 1.0))
    assert time_verdict(loose).confidence is not Confidence.HIGH


def test_an_environment_warning_caps_confidence_at_medium():
    verdict = time_verdict(analysis("user"), conditions=Conditions(environment_warned=True))
    assert verdict.confidence is Confidence.MEDIUM


def space_verdict(user: TargetAnalysis, rungs: Ladder, conditions: Conditions = CLEAN):
    return judge(user, rungs, conditions).space


def test_the_same_memory_band_as_optimal_says_so():
    rungs = ladder(analysis("hash-map", memory_exponent=1.0))
    verdict = space_verdict(analysis("user", memory_exponent=1.0), rungs)
    assert verdict.message == "space linear, same as hash-map"


def test_less_memory_than_optimal_says_so():
    rungs = ladder(analysis("hash-map", memory_exponent=1.0))
    verdict = space_verdict(analysis("user", memory_exponent=0.0), rungs)
    assert verdict.message == "space constant, less than hash-map (linear)"


def test_more_memory_than_optimal_says_so():
    rungs = ladder(analysis("hash-map", memory_exponent=0.0))
    verdict = space_verdict(analysis("user", memory_exponent=1.0), rungs)
    assert verdict.message == "space linear, hash-map is constant"


def test_a_leaner_approach_in_the_optimal_time_band_is_named():
    lean = analysis("two-pointers", memory_exponent=0.0)
    rungs = ladder(analysis("hash-map", memory_exponent=1.0), lean)
    verdict = space_verdict(analysis("user", memory_exponent=1.0), rungs)
    assert verdict.message == (
        "space linear, same as hash-map; a constant-space optimal exists: two-pointers"
    )


def test_a_leaner_approach_in_a_slower_band_is_not_named():
    lean_but_slow = analysis("brute-force", 2.0, memory_exponent=0.0)
    rungs = ladder(analysis("hash-map", memory_exponent=1.0), lean_but_slow)
    verdict = space_verdict(analysis("user", memory_exponent=1.0), rungs)
    assert verdict.message == "space linear, same as hash-map"


def test_missing_memory_figures_leave_space_unknown():
    verdict = space_verdict(analysis("user"), ladder(OPTIMAL))
    assert (verdict.band, verdict.message) == (None, "space unknown: not enough memory figures")


def test_clean_memory_figures_give_high_confidence():
    rungs = ladder(analysis("hash-map", memory_exponent=1.0))
    assert space_verdict(analysis("user", memory_exponent=1.0), rungs).confidence is Confidence.HIGH


def test_the_runtime_caps_memory_confidence():
    rungs = ladder(analysis("hash-map", memory_exponent=1.0))
    conditions = Conditions(memory_cap=Confidence.LOW)
    verdict = space_verdict(analysis("user", memory_exponent=1.0), rungs, conditions)
    assert verdict.confidence is Confidence.LOW


def approach(declared: ComplexityClass, approach_id: str = "hash-map") -> Approach:
    return Approach(approach_id, "Name", ApproachRole.OPTIMAL, "O(?)", "O(?)", declared, declared)


def test_a_measured_band_matching_the_declared_class_is_consistent():
    check = check_ladder(approach(ComplexityClass.LINEAR), analysis("hash-map", 1.0))
    assert check.status is LadderStatus.CONSISTENT


def test_n_log_n_shares_the_linear_band():
    check = check_ladder(approach(ComplexityClass.LINEARITHMIC), analysis("hash-map", 1.0))
    assert check.status is LadderStatus.CONSISTENT


def test_a_measured_band_contradicting_the_declared_class_fails():
    check = check_ladder(approach(ComplexityClass.QUADRATIC), analysis("hash-map", 1.0))
    assert (check.status, check.message) == (
        LadderStatus.CONTRADICTS,
        "hash-map declares O(n^2) but measures ~n|nlogn (slope 1.00); "
        "time / n^2 varies 50x, more than the 4x tolerance",
    )


def fixed_cost_then_linear(target_id: str) -> TargetAnalysis:
    stats = tuple(
        SizeStats(size, SizeStatus.COMPLETED, 10_000.0 + 10.0 * size, 0.02, calls=CALLS)
        for size in SIZES
    )
    return analyze(TargetSeries(target_id, stats))


def test_a_band_explained_by_a_fixed_cost_is_tolerated():
    check = check_ladder(approach(ComplexityClass.LINEAR), fixed_cost_then_linear("hash-map"))
    assert check.status is LadderStatus.TOLERATED


def test_a_tolerated_band_names_the_drift():
    check = check_ladder(approach(ComplexityClass.LINEAR), fixed_cost_then_linear("hash-map"))
    assert check.message == (
        "hash-map declares O(n) and measures ~1|log n|sqrt n (slope 0.66), "
        "but time / n varies only 1.0x, within the 4x tolerance"
    )


def test_a_band_mismatch_on_a_narrow_ladder_is_tolerated():
    rung = analysis("hash-map", 1.5, sizes=(1000, 2000, 5000, 10_000))
    check = check_ladder(approach(ComplexityClass.LINEAR), rung)
    assert check.status is LadderStatus.TOLERATED


def test_a_drift_just_over_the_tolerance_never_reads_as_the_tolerance():
    stats = tuple(
        SizeStats(size, SizeStatus.COMPLETED, value, 0.02, calls=CALLS)
        for size, value in ((100, 1000.0), (110, 1000.0), (121, 4040.0))
    )
    check = check_ladder(approach(ComplexityClass.CONSTANT), analyze(TargetSeries("s", stats)))
    assert check.message.endswith("time / 1 varies 4.1x, more than the 4x tolerance")


def test_exponential_classes_are_checked_by_band_alone():
    check = check_ladder(approach(ComplexityClass.EXPONENTIAL), analysis("hash-map", 3.0))
    assert check.status is LadderStatus.CONTRADICTS


def test_too_few_sizes_leave_an_approach_unclassified():
    rung = analysis("brute-force", 2.0, exceeded_at=10_000)
    check = check_ladder(approach(ComplexityClass.QUADRATIC, "brute-force"), rung)
    assert (check.status, check.message) == (
        LadderStatus.UNCLASSIFIED,
        "brute-force: 2 usable sizes (budget exceeded at n=1e4); "
        "add smaller sizes to perf.size_ladder to classify it",
    )


RAN_AT = datetime(2026, 9, 12, tzinfo=UTC)


def test_no_previous_run_has_no_history():
    assert compare_history({100_000: 10.0}, []) is None


def test_history_compares_with_the_best_previous_run_at_the_largest_common_size():
    past = [PastRun(RAN_AT, {100_000: 13.0, 1000: 1.0}), PastRun(RAN_AT, {1000: 0.5})]
    history = compare_history({1000: 0.9, 100_000: 11.83}, past)
    assert history is not None
    assert (history.size, history.best_previous_ns, history.change) == (
        100_000,
        13.0,
        pytest.approx(-0.09),
    )


def test_history_ranks_the_current_run_among_the_runs_at_that_size():
    past = [PastRun(RAN_AT, {1000: 0.5}), PastRun(RAN_AT, {1000: 2.0})]
    history = compare_history({1000: 1.0}, past)
    assert history is not None
    assert (history.rank, history.runs) == (2, 3)
