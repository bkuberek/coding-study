"""D10: a virtual-clock case gives the same outputs in every run of the reference, and its slowest
run stays within a quarter of its hang guard (docs/specs/authoring.md#dynamic)."""

import pytest

from coding_study.domain.cases import Expected, FunctionInput, JsonValue
from coding_study.domain.clock_determinism import (
    DETERMINISM_RUNS,
    DeterminismVerdict,
    judge_determinism,
)
from coding_study.domain.comparators import comparator_for
from coding_study.domain.judging import Judgement, RunnableCase, judge
from coding_study.domain.problem import ComparatorSpec, ComparatorType
from coding_study.domain.runs import CaseReport, JobReport, Raised, Returned, Stalled, UserError

EXACT = comparator_for(ComparatorSpec(ComparatorType.EXACT))
MS = 1_000_000
GUARD_MS = 1_000
CASES = [
    RunnableCase("ex1", FunctionInput({}), Expected(["a"])),
    RunnableCase("ex2", FunctionInput({}), Expected(["b"])),
]
GUARDS = {"ex1": GUARD_MS, "ex2": GUARD_MS}
LEVELS = {"ex1": 1, "ex2": 2}


def run_of(*outcomes) -> Judgement:
    reports = tuple(
        CaseReport(case.id, outcome) for case, outcome in zip(CASES, outcomes, strict=True)
    )
    return judge(CASES, JobReport("job", reports), EXACT)


def returned(output: JsonValue, milliseconds: float = 2) -> Returned:
    return Returned(output, int(milliseconds * MS))


def verdict_of(*runs: Judgement) -> DeterminismVerdict:
    return judge_determinism(runs, GUARDS, LEVELS)


def identical(count: int = DETERMINISM_RUNS) -> list[Judgement]:
    return [run_of(returned(["a"]), returned(["b"])) for _ in range(count)]


def test_the_reference_runs_ten_times():
    assert DETERMINISM_RUNS == 10


def test_runs_that_agree_pass():
    verdict = verdict_of(*identical())
    assert (verdict.passed, verdict.runs, verdict.agreeing, verdict.failures) == (
        True,
        10,
        10,
        (),
    )


def test_the_slowest_run_is_a_share_of_its_cases_hang_guard():
    runs = [*identical(9), run_of(returned(["a"], 2), returned(["b"], 150))]
    assert verdict_of(*runs).slowest_share == pytest.approx(0.15)


def test_a_share_is_taken_against_the_guard_of_its_own_case():
    runs = [*identical(9), run_of(returned(["a"], 100), returned(["b"], 2))]
    verdict = judge_determinism(runs, {"ex1": 2_000, "ex2": 10}, LEVELS)
    assert verdict.slowest_share == pytest.approx(0.2)


def test_a_slowest_run_over_a_quarter_of_the_guard_fails():
    runs = [*identical(9), run_of(returned(["a"]), returned(["b"], 300))]
    verdict = verdict_of(*runs)
    assert (verdict.passed, verdict.failures) == (
        False,
        (
            "level 2 ex2: the slowest run took 300 ms, 30% of its hang guard of 1000 ms; "
            "at most 25%",
        ),
    )


def test_a_slowest_run_at_exactly_a_quarter_of_the_guard_passes():
    runs = [*identical(9), run_of(returned(["a"]), returned(["b"], 250))]
    assert verdict_of(*runs).passed


def test_runs_that_differ_fail_naming_every_output_and_its_runs():
    runs = [*identical(7), *(run_of(returned(["a"]), returned(["x"])) for _ in range(3))]
    verdict = verdict_of(*runs)
    assert (verdict.passed, verdict.agreeing, verdict.failures) == (
        False,
        7,
        (
            'level 2 ex2: outputs differ between runs: returned ["b"] in 7 of 10 runs, '
            'returned ["x"] in 3 of 10 runs',
        ),
    )


def test_the_most_common_output_comes_first():
    runs = [*(run_of(returned(["a"]), returned(["x"])) for _ in range(6)), *identical(4)]
    [failure] = verdict_of(*runs).failures
    assert failure.index('["x"] in 6 of') < failure.index('["b"] in 4 of')


def test_the_agreeing_runs_are_the_fewest_any_case_has():
    runs = [
        *(run_of(returned(["a"]), returned(["b"])) for _ in range(8)),
        run_of(returned(["x"]), returned(["b"])),
        run_of(returned(["y"]), returned(["z"])),
    ]
    assert verdict_of(*runs).agreeing == 8


def test_an_error_in_one_run_is_a_different_output():
    error = Raised(UserError("RuntimeError", "late"), 2 * MS, op_index=3)
    runs = [*identical(9), run_of(returned(["a"]), error)]
    [failure] = verdict_of(*runs).failures
    assert failure == (
        'level 2 ex2: outputs differ between runs: returned ["b"] in 9 of 10 runs, '
        "RuntimeError: late at op 3 in 1 of 10 runs"
    )


def test_a_deadlock_in_one_run_is_a_different_output():
    stalled = Stalled((), 2 * MS, op_index=3, reason="op 3 (@join r1): deadlock at 2000 ms")
    runs = [*identical(9), run_of(stalled, returned(["b"]))]
    [failure] = verdict_of(*runs).failures
    assert failure.endswith("op 3 (@join r1): deadlock at 2000 ms in 1 of 10 runs")


def test_outputs_that_differ_only_past_the_summary_length_still_differ():
    long = ["a" * 300]
    runs = [run_of(returned([*long, "1"]), returned(["b"])) for _ in range(9)]
    runs.append(run_of(returned([*long, "2"]), returned(["b"])))
    assert not verdict_of(*runs).passed


def test_each_failing_case_is_named_once_in_case_order():
    runs = [
        *(run_of(returned(["a"]), returned(["b"])) for _ in range(9)),
        run_of(returned(["x"]), returned(["y"])),
    ]
    assert [failure.split(":")[0] for failure in verdict_of(*runs).failures] == [
        "level 1 ex1",
        "level 2 ex2",
    ]


def test_a_case_that_differs_and_is_slow_reports_both():
    runs = [*identical(9), run_of(returned(["x"], 600), returned(["b"]))]
    [differs, slow] = verdict_of(*runs).failures
    assert (differs.startswith("level 1 ex1: outputs differ"), "600 ms, 60%" in slow) == (
        True,
        True,
    )


def test_a_case_without_a_measured_duration_has_no_share():
    stalled = Stalled((), 0)
    verdict = verdict_of(*[run_of(stalled, stalled)] * 3)
    assert verdict.slowest_share is None
