import pytest

from coding_study.domain.cases import (
    Case,
    Expected,
    FunctionInput,
    GeneratedInput,
    JsonValue,
    OperationSequence,
)
from coding_study.domain.comparators import Mismatch, comparator_for
from coding_study.domain.judging import (
    CaseStatus,
    RunnableCase,
    Tally,
    concrete_case,
    judge,
    outcome_summary,
    with_oracle,
    with_time_limits,
)
from coding_study.domain.problem import ComparatorSpec, ComparatorType
from coding_study.domain.runs import (
    CaseReport,
    Crashed,
    InvalidOutput,
    JobReport,
    NotRun,
    Raised,
    Returned,
    TimedOut,
    UserError,
)
from coding_study.domain.time_limits import (
    AbsoluteTimeLimit,
    Calibration,
    CaseLimit,
    FactorTimeLimit,
    TimeLimits,
)

EXACT = comparator_for(ComparatorSpec(ComparatorType.EXACT))
INPUT = FunctionInput({"value": 1})


def runnable(case_id: str, expected: JsonValue = 1, *, visible: bool = False) -> RunnableCase:
    return RunnableCase(case_id, INPUT, Expected(expected), visible=visible)


def judged(*outcomes, cases=None):
    cases = cases or [runnable(f"c{index}") for index in range(len(outcomes))]
    reports = tuple(
        CaseReport(case.id, outcome) for case, outcome in zip(cases, outcomes, strict=True)
    )
    return judge(cases, JobReport("job", reports), EXACT)


def statuses(judgement) -> list[CaseStatus]:
    return [verdict.status for verdict in judgement.verdicts]


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        (Returned(1, 10), CaseStatus.PASS),
        (Returned(2, 10), CaseStatus.FAIL),
        (Raised(UserError("ValueError", "bad"), 10), CaseStatus.ERROR),
        (InvalidOutput("cyclic", 10), CaseStatus.INVALID),
        (TimedOut(10_000), CaseStatus.TIMEOUT),
        (Crashed(137, ("killed",)), CaseStatus.ERROR),
        (NotRun("restarted 3 times"), CaseStatus.NOT_RUN),
    ],
)
def test_each_runner_outcome_gets_a_status(outcome, status):
    assert statuses(judged(outcome)) == [status]


def test_wrong_answers_carry_the_mismatch():
    verdict = judged(Returned([1, 3], 10), cases=[runnable("c0", [1, 2])]).verdicts[0]
    assert verdict.mismatch == Mismatch("first difference at index 1", first_difference=1)


def test_passing_cases_carry_no_mismatch():
    assert judged(Returned(1, 10)).verdicts[0].mismatch is None


def test_verdicts_keep_the_case_order():
    cases = [runnable("b"), runnable("a")]
    judgement = judged(Returned(1, 1), Returned(1, 1), cases=cases)
    assert [verdict.case.id for verdict in judgement.verdicts] == ["b", "a"]


def test_a_case_missing_from_the_report_is_not_run():
    judgement = judge([runnable("c0")], JobReport("job"), EXACT)
    assert statuses(judgement) == [CaseStatus.NOT_RUN]


@pytest.mark.parametrize(
    ("outcome", "duration"),
    [
        (Returned(1, 41_000), 41_000),
        (Raised(UserError("E", "m"), 7), 7),
        (InvalidOutput("x", 9), 9),
        (TimedOut(100), None),
        (Crashed(1), None),
        (NotRun("x"), None),
    ],
)
def test_verdicts_expose_the_measured_duration(outcome, duration):
    assert judged(outcome).verdicts[0].duration_ns == duration


def test_load_error_replaces_every_verdict():
    error = UserError("ImportError", "no module")
    judgement = judge([runnable("c0")], JobReport("job", load_error=error), EXACT)
    assert (judgement.verdicts, judgement.load_error) == ((), error)


def test_tally_counts_each_kind_of_result():
    judgement = judged(
        Returned(1, 1),
        Returned(2, 1),
        InvalidOutput("x", 1),
        Raised(UserError("E", "m"), 1),
        Crashed(1),
        NotRun("x"),
        TimedOut(5),
    )
    assert judgement.tally() == Tally(total=7, passed=1, failed=2, errored=3, timed_out=1)


def test_tally_of_a_load_error_counts_every_case_as_errored():
    judgement = judge(
        [runnable("a"), runnable("b")], JobReport("job", load_error=UserError("E", "m")), EXACT
    )
    assert judgement.tally() == Tally(total=2, errored=2)


def test_all_passed_when_every_case_passes():
    assert judged(Returned(1, 1), Returned(1, 1)).passed


def test_not_all_passed_with_one_failure():
    assert not judged(Returned(1, 1), Returned(2, 1)).passed


def test_not_all_passed_after_a_load_error():
    judgement = judge([runnable("a")], JobReport("job", load_error=UserError("E", "m")), EXACT)
    assert not judgement.passed


def test_count_by_status():
    judgement = judged(Returned(1, 1), Returned(2, 1), Returned(2, 1))
    assert judgement.count(CaseStatus.FAIL) == 2


def test_concrete_case_keeps_the_case_fields():
    case = Case("h1", INPUT, Expected([0]), visible=True, hang_guard_ms=500, note="zeros")
    assert concrete_case(case) == RunnableCase(
        "h1", INPUT, Expected([0]), visible=True, hang_guard_ms=500, note="zeros"
    )


def test_concrete_case_accepts_operation_sequences():
    ops = OperationSequence(("Box",), ((),))
    assert concrete_case(Case("ex1", ops, Expected([None]))).input == ops


def test_concrete_case_rejects_generated_inputs():
    with pytest.raises(ValueError, match="generated"):
        concrete_case(Case("g1", GeneratedInput(10, 1)))


@pytest.mark.parametrize(
    ("outcome", "summary"),
    [
        (Returned([1], 1), "returned [1]"),
        (Raised(UserError("KeyError", "3"), 1), "KeyError: 3"),
        (Raised(UserError("E", "m"), 1, op_index=2), "E: m at op 2"),
        (InvalidOutput("cyclic", 1), "invalid output: cyclic"),
        (TimedOut(500), "timed out after 500 ms"),
        (Crashed(137), "runner crashed with exit code 137"),
        (NotRun("restarted"), "not run: restarted"),
    ],
)
def test_outcome_summaries(outcome, summary):
    assert outcome_summary(outcome) == summary


MS = 1_000_000
LIMITS = TimeLimits(AbsoluteTimeLimit(50), 100)


def test_passing_case_over_the_time_limit_is_tle():
    assert statuses(with_time_limits(judged(Returned(1, 51 * MS)), LIMITS)) == [CaseStatus.TLE]


def test_passing_case_at_exactly_the_time_limit_passes():
    assert statuses(with_time_limits(judged(Returned(1, 50 * MS)), LIMITS)) == [CaseStatus.PASS]


def test_wrong_answer_over_the_time_limit_stays_a_failure():
    assert statuses(with_time_limits(judged(Returned(2, 90 * MS)), LIMITS)) == [CaseStatus.FAIL]


def test_tle_verdict_keeps_the_limit_it_exceeded():
    verdict = with_time_limits(judged(Returned(1, 90 * MS)), LIMITS).verdicts[0]
    assert verdict.time_limit == CaseLimit(50, "")


def test_case_without_a_limit_is_not_timed():
    limits = TimeLimits(FactorTimeLimit(5), 100, Calibration("hash-map", {}))
    assert statuses(with_time_limits(judged(Returned(1, 90 * MS)), limits)) == [CaseStatus.PASS]


def test_tle_counts_in_its_own_tally_column():
    judgement = with_time_limits(judged(Returned(1, 90 * MS), Returned(1, MS)), LIMITS)
    assert judgement.tally() == Tally(total=2, passed=1, tle=1)


def test_tle_fails_the_judgement():
    assert not with_time_limits(judged(Returned(1, 90 * MS)), LIMITS).passed


def test_time_limits_leave_a_load_error_unchanged():
    judgement = judge([runnable("c0")], JobReport("job", load_error=UserError("E", "x")), EXACT)
    assert with_time_limits(judgement, LIMITS) == judgement


def test_oracle_verdicts_follow_the_case_verdicts():
    cases, oracle = judged(Returned(1, 1)), judged(Returned(2, 1), cases=[runnable("oracle-1")])
    assert [verdict.case.id for verdict in with_oracle(cases, oracle).verdicts] == [
        "c0",
        "oracle-1",
    ]


def test_oracle_inputs_count_as_cases():
    cases, oracle = judged(Returned(1, 1)), judged(Returned(2, 1), cases=[runnable("oracle-1")])
    assert with_oracle(cases, oracle).tally() == Tally(total=2, passed=1, failed=1)


def test_a_load_error_leaves_the_oracle_inputs_unrun():
    error = UserError("ImportError", "no module")
    loading = judge([runnable("c0")], JobReport("job", load_error=error), EXACT)
    oracle = judge([runnable("oracle-1")], JobReport("job", load_error=error), EXACT)
    assert with_oracle(loading, oracle).tally() == Tally(total=2, errored=2)
