"""Stress runs judged from fabricated runner results on a two-worker queue scenario."""

from dataclasses import replace

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, JsonValue, OperationSequence
from coding_study.domain.comparators import comparator_for
from coding_study.domain.concurrency import Concurrency, ConcurrencyModel, StressVariant
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language
from coding_study.domain.runs import (
    CaseOutcome,
    CaseReport,
    JobReport,
    Raised,
    SectionCounters,
    Stalled,
    StressCompleted,
    StressFailure,
    StressPhase,
    UserError,
    WorkerProgress,
)
from coding_study.domain.stress import (
    ArithmeticSequence,
    Bounds,
    CheckerInvariant,
    Count,
    Distinct,
    EqualMultisets,
    FinalSequence,
    Invariant,
    Literal,
    Repeat,
    Scope,
    SectionBounds,
    Selector,
    SourceOrder,
    Step,
    StressScenario,
    Sum,
    WorkerGroup,
)
from coding_study.domain.stress_runs import CaseRuns, PlannedRun
from coding_study.domain.stress_verdict import StressJudging, judge_run, judge_stress

PUT_VALUES = Selector("put", "arg0")
TAKEN = Selector("take")
JUDGING = StressJudging(comparator_for(ComparatorSpec(ComparatorType.OPS)))
CONCURRENCY = Concurrency({Language.PYTHON: ConcurrencyModel.THREADS})


def scenario(*invariants: Invariant, final: FinalSequence | None = None) -> StressScenario:
    """One producer puts 1, 2; one consumer takes twice; then `size` runs once."""
    return StressScenario(
        setup=OperationSequence(("Queue",), ((2,),)),
        workers=(
            WorkerGroup("producer", 1, Repeat(2), (Step("put", (ArithmeticSequence(1),)),)),
            WorkerGroup("consumer", 1, Repeat(2), (Step("take", ()),)),
        ),
        invariants=invariants,
        final=final or FinalSequence(("size",), ((),)),
        document={"seed": 1},
    )


def planned(case_scenario: StressScenario, runs: int = 1) -> tuple[PlannedRun, ...]:
    case = Case("s1", case_scenario)
    return CaseRuns(case, CONCURRENCY, Language.PYTHON, StressVariant.THREAD).plan(
        tuple(range(1, runs + 1))
    )


def completed(
    taken: tuple[JsonValue, JsonValue] = (1, 2),
    final: tuple[JsonValue, ...] = (0,),
    sections: dict[str, SectionCounters] | None = None,
) -> StressCompleted:
    return StressCompleted(
        setup=(None,),
        workers=((None, None), taken),
        final=final,
        sections=sections or {},
        duration_ns=2_000_000,
    )


def reasons(case_scenario: StressScenario, outcome: CaseOutcome) -> tuple[str, ...]:
    return judge_run(planned(case_scenario)[0], outcome, JUDGING).reasons


def status(case_scenario: StressScenario, outcome: CaseOutcome) -> CaseStatus:
    return judge_run(planned(case_scenario)[0], outcome, JUDGING).status


def test_a_run_satisfying_every_invariant_passes():
    invariants = (EqualMultisets(PUT_VALUES, TAKEN), Distinct(TAKEN))
    assert status(scenario(*invariants), completed()) is CaseStatus.PASS


def test_equal_multisets_names_missing_and_extra_values():
    found = reasons(scenario(EqualMultisets(PUT_VALUES, TAKEN)), completed(taken=(1, 1)))
    assert found == ("equal_multisets put.arg0 vs take: 1 missing (2), 1 extra (1)",)


def test_distinct_names_the_repeated_value():
    found = reasons(scenario(Distinct(TAKEN)), completed(taken=(2, 2)))
    assert found == ("distinct take: 2 (2 times)",)


def test_values_compare_type_strictly():
    found = reasons(scenario(EqualMultisets(PUT_VALUES, TAKEN)), completed(taken=(True, 2)))
    assert found[0].startswith("equal_multisets put.arg0 vs take: 1 missing (1)")


def test_bounds_are_inclusive():
    within = Bounds(Selector("size", scope=Scope.FINAL), minimum=0, maximum=0)
    assert status(scenario(within), completed()) is CaseStatus.PASS


def test_bounds_name_values_outside():
    bounds = Bounds(TAKEN, minimum=0, maximum=1)
    assert reasons(scenario(bounds), completed()) == ("bounds take: 2 outside [0, 1]",)


def test_count_with_equals():
    count = Count(TAKEN, equals=3)
    assert reasons(scenario(count), completed()) == ("count take: 2, expected 3",)


def test_sum_within_bounds_passes():
    assert status(scenario(Sum(TAKEN, minimum=3, maximum=3)), completed()) is CaseStatus.PASS


def test_sum_outside_bounds_fails():
    found = reasons(scenario(Sum(TAKEN, maximum=2)), completed())
    assert found == ("sum take: 3 outside [-inf, 2]",)


def test_source_order_requires_increasing_values_per_source():
    order = SourceOrder(TAKEN, stride=1000)
    found = reasons(scenario(order), completed(taken=(2, 1)))
    assert found == ("source_order take: consumer[0] got 1 after 2",)


def test_source_order_ignores_values_from_other_sources():
    order = SourceOrder(TAKEN, stride=1)
    assert status(scenario(order), completed(taken=(2, 1))) is CaseStatus.PASS


def test_a_group_selector_reads_only_that_group():
    count = Count(Selector("take", group="producer"), equals=0)
    assert status(scenario(count), completed()) is CaseStatus.PASS


def test_section_violations_fail_the_run():
    section = SectionBounds("data")
    counters = {"data": SectionCounters(entries=4, violations=2, max_occupancy=2)}
    found = reasons(scenario(section), completed(sections=counters))
    assert found == ("section data: 2 violations in 4 entries (at most 0)",)


def test_section_min_occupancy_detects_serialization():
    section = SectionBounds("data", min_occupancy=2)
    counters = {"data": SectionCounters(entries=4, violations=0, max_occupancy=1)}
    found = reasons(scenario(section), completed(sections=counters))
    assert found == ("section data: max occupancy 1, at least 2 expected",)


def test_a_section_never_entered_has_zero_counters():
    section = SectionBounds("data", min_occupancy=1)
    assert status(scenario(section), completed()) is CaseStatus.FAIL


def test_final_expected_mismatch_fails_the_run():
    final = FinalSequence(("size",), ((),), expected=(0,))
    found = reasons(scenario(final=final), completed(final=(1,)))
    assert found == ("final: op 0 size: expected 0, got 1",)


def test_a_checker_invariant_reads_the_run_record():
    seen: list[dict[str, JsonValue]] = []

    def check(name: str, scenario_document: dict[str, JsonValue], run: dict[str, JsonValue]):
        seen.append(run)
        return None if name == "ok" else "wrong"

    judging = replace(JUDGING, checker=check)
    result = judge_run(planned(scenario(CheckerInvariant("ok")))[0], completed(), judging)
    assert (result.status, seen[0]["workers"][1]["ops"][0]) == (  # type: ignore[index]
        CaseStatus.PASS,
        {"op": "take", "args": [], "output": 1},
    )


def test_a_checker_that_raises_fails_the_run():
    def check(name: str, scenario_document: dict[str, JsonValue], run: dict[str, JsonValue]):
        raise KeyError(name)

    judging = replace(JUDGING, checker=check)
    result = judge_run(planned(scenario(CheckerInvariant("x")))[0], completed(), judging)
    assert result.reasons == ("checker x raised KeyError: 'x'",)


def test_a_worker_error_names_the_worker_and_op():
    error = Raised(
        UserError("IndexError", "pop from an empty deque"),
        10,
        stress=StressFailure(StressPhase.WORKER, 1, worker=1),
    )
    assert reasons(scenario(), error) == (
        "consumer[0] op 1 (take): IndexError: pop from an empty deque",
    )


def test_a_stall_names_where_the_workers_wait():
    stalled = Stalled((WorkerProgress(0, 1, True), WorkerProgress(1, 0, True)), 5_000_000_000)
    assert reasons(scenario(), stalled) == (
        "producer[0] in put (op 1 of 2) · consumer[0] in take (op 0 of 2)",
    )


def test_a_stall_has_its_own_status():
    assert status(scenario(), Stalled((), 0)) is CaseStatus.STALLED


def test_a_case_passes_only_when_every_run_passes():
    runs = planned(scenario(Distinct(TAKEN)), runs=3)
    outcomes = [completed(), completed(taken=(1, 1)), completed()]
    job = JobReport(
        "job",
        tuple(CaseReport(run.run_id, outcome) for run, outcome in zip(runs, outcomes, strict=True)),
    )
    (verdict,) = judge_stress(runs, job, JUDGING)
    assert (verdict.status, verdict.runs_passed, verdict.failures[0].seed) == (
        CaseStatus.FAIL,
        2,
        2,
    )


def test_the_slowest_run_is_reported_as_a_share_of_the_deadline():
    runs = planned(scenario(), runs=1)
    job = JobReport("job", (CaseReport(runs[0].run_id, completed()),))
    (verdict,) = judge_stress(runs, job, JUDGING)
    assert verdict.slowest_share == 2_000_000 / 5_000_000_000


def test_a_run_without_a_result_is_not_run():
    runs = planned(scenario(), runs=1)
    (verdict,) = judge_stress(runs, JobReport("job"), JUDGING)
    assert verdict.status is CaseStatus.NOT_RUN


def test_literal_steps_are_recorded_with_their_arguments():
    case_scenario = replace(
        scenario(EqualMultisets(PUT_VALUES, TAKEN)),
        workers=(
            WorkerGroup("producer", 1, Repeat(2), (Step("put", (Literal(9),)),)),
            WorkerGroup("consumer", 1, Repeat(2), (Step("take", ()),)),
        ),
    )
    assert status(case_scenario, completed(taken=(9, 9))) is CaseStatus.PASS
