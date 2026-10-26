import pytest

from coding_study.domain.bench_records import (
    BenchOutcome,
    MachineState,
    PowerSource,
    bench_seed,
    input_elements,
    max_batch,
)
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.problem import Language


def test_a_seed_is_the_same_in_every_run():
    assert bench_seed("two-sum", 1000) == bench_seed("two-sum", 1000)


def test_seeds_differ_by_size():
    assert bench_seed("two-sum", 1000) != bench_seed("two-sum", 10_000)


def test_seeds_differ_by_problem():
    assert bench_seed("two-sum", 1000) != bench_seed("three-sum", 1000)


@pytest.mark.parametrize(
    ("elements", "language", "calls"),
    [
        (10, Language.PYTHON, 100_000),
        (100, Language.PYTHON, 10_000),
        (100, Language.JAVA, 100_000),
        (100, Language.TYPESCRIPT, 100_000),
        (1000, Language.KOTLIN, 10_000),
        (10**6, Language.PYTHON, 1),
        (10**8, Language.JAVA, 1),
    ],
)
def test_batches_hold_a_bounded_number_of_input_elements(elements, language, calls):
    assert max_batch(elements, language) == calls


@pytest.mark.parametrize(
    ("document", "elements"),
    [
        pytest.param({"n": 100_000}, 1, id="one integer, whatever its value"),
        pytest.param({"nums": [3, 1, 2], "target": 4}, 4, id="list items and a scalar"),
        pytest.param({"s": "abcd"}, 4, id="string characters"),
        pytest.param({"grid": [[1, 2], [3, 4]]}, 4, id="nested list leaves"),
        pytest.param({"ops": ["Set", "add"], "args": [[], [7]]}, 7, id="op names and args"),
        pytest.param({"nums": []}, 1, id="empty input"),
    ],
)
def test_input_elements_count_what_a_decoded_copy_holds(document, elements):
    assert input_elements(document) == elements


def test_a_quiet_machine_on_power_has_no_warning():
    assert MachineState("cpu", PowerSource.AC, 2.0, 8).warnings == ()


def test_battery_power_is_a_warning():
    assert MachineState("cpu", PowerSource.BATTERY, 2.0, 8).warnings == ("on battery power",)


def test_a_load_above_half_the_cores_is_a_warning():
    warnings = MachineState("cpu", PowerSource.AC, 4.5, 8).warnings
    assert warnings == ("load 4.5 is above half of 8 cores",)


def test_a_load_of_exactly_half_the_cores_is_fine():
    assert MachineState("cpu", PowerSource.AC, 4.0, 8).warnings == ()


def test_an_unknown_load_is_no_warning():
    assert MachineState("cpu", PowerSource.UNKNOWN, None, 8).warnings == ()


@pytest.mark.parametrize("confidence", [Confidence.MEDIUM, Confidence.HIGH])
def test_suboptimal_at_medium_or_high_confidence_is_confident(confidence):
    assert BenchOutcome(Verdict.SUBOPTIMAL, confidence).is_confident_suboptimal


def test_suboptimal_at_low_confidence_is_not_confident():
    assert not BenchOutcome(Verdict.SUBOPTIMAL, Confidence.LOW).is_confident_suboptimal


@pytest.mark.parametrize("verdict", [Verdict.OPTIMAL, Verdict.NEAR_OPTIMAL, Verdict.UNKNOWN])
def test_other_verdicts_are_never_confident_suboptimal(verdict):
    assert not BenchOutcome(verdict, Confidence.HIGH).is_confident_suboptimal
