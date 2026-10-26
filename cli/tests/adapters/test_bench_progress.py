"""`BenchProgress` fed events directly: protocol checks and restart bookkeeping."""

import pytest

from coding_study.adapters.bench_progress import BenchProgress
from coding_study.adapters.runner_protocol import (
    BenchBudgetExceeded,
    BenchError,
    BenchSampleEvent,
    BenchStart,
    Bye,
    CaseStart,
    Hello,
    JobStart,
)
from coding_study.domain.bench_runs import (
    BenchInput,
    BenchJob,
    BenchRequest,
    BenchSample,
    BenchSettings,
    BenchTarget,
    Warmup,
)
from coding_study.domain.cases import FunctionInput
from coding_study.domain.errors import RunnerProtocolError
from coding_study.domain.naming import FunctionNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import Crashed, FileTarget, Raised, TimedOut, UserError
from coding_study.domain.signature import FunctionSignature, Param, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType

INT = ScalarType(Scalar.INT)
NAMES = FunctionNames("echo", {"value": "value"})
HELLO = Hello("python", 1, "3.13")
JOB = BenchJob(
    job_id="echo",
    kind=ProblemKind.FUNCTION,
    signature=FunctionSignature("echo", (Param("value", INT),), Returns(INT)),
    targets=(
        BenchTarget("a", FileTarget("/a.py"), NAMES),
        BenchTarget("b", FileTarget("/b.py"), NAMES),
    ),
    inputs=tuple(BenchInput(size, FunctionInput({"value": size}), 1) for size in (1, 2)),
    settings=BenchSettings(1, Warmup(1, 1, 0.05), 2000, False, 0),
    hang_guard_ms=500,
)


@pytest.fixture
def progress() -> BenchProgress:
    progress = BenchProgress(BenchRequest(JOB))
    progress.begin_attempt()
    return progress


def started(progress: BenchProgress) -> BenchProgress:
    progress.apply(HELLO)
    progress.apply(JobStart("echo"))
    return progress


def test_events_before_hello_break_the_protocol(progress):
    with pytest.raises(RunnerProtocolError, match="before hello"):
        progress.apply(JobStart("echo"))


def test_case_events_break_the_bench_protocol(progress):
    with pytest.raises(RunnerProtocolError, match="in bench mode"):
        started(progress).apply(CaseStart("echo", "c1"))


def test_events_for_an_unknown_target_break_the_protocol(progress):
    with pytest.raises(RunnerProtocolError, match="unexpected bench event"):
        started(progress).apply(BenchStart("echo", "zzz", 1))


def test_events_for_a_size_not_requested_break_the_protocol(progress):
    with pytest.raises(RunnerProtocolError, match="unexpected bench event"):
        started(progress).apply(BenchStart("echo", "a", 7))


def test_no_call_is_in_progress_before_the_first_bench_start(progress):
    assert started(progress).call_limit_ms is None


def test_a_bench_start_puts_the_hang_guard_in_force(progress):
    started(progress).apply(BenchStart("echo", "a", 1))
    assert progress.call_limit_ms == 500


def test_a_crash_before_any_call_is_charged_to_the_first_running_target(progress):
    started(progress).interrupt(Crashed(9))
    measured = progress.report().target("a").at(1)
    assert measured is not None
    assert isinstance(measured.failure, Crashed)


def test_a_hang_is_charged_to_the_call_in_progress(progress):
    started(progress).apply(BenchStart("echo", "b", 2))
    progress.interrupt(TimedOut(500))
    measured = progress.report().target("b").at(2)
    assert measured is not None
    assert measured.exceeded_ns == 500_000_000


def test_the_restart_resumes_at_the_interrupted_size_without_the_stopped_target(progress):
    started(progress).apply(BenchStart("echo", "b", 2))
    progress.interrupt(TimedOut(500))
    request = progress.begin_attempt()
    job = request["jobs"][0]  # type: ignore[index]
    assert ([t["target_id"] for t in job["targets"]], [i["size"] for i in job["inputs"]]) == (  # type: ignore[index]
        ["a"],
        [2],
    )


def test_samples_at_the_restart_size_are_measured_again(progress):
    started(progress).apply(BenchStart("echo", "a", 2))
    progress.apply(BenchSampleEvent("echo", "a", 2, BenchSample(1, 10, 10, 1)))
    progress.apply(BenchStart("echo", "b", 2))
    progress.interrupt(TimedOut(500))
    progress.begin_attempt()
    measured = progress.report().target("a").at(2)
    assert measured is None


def test_the_run_is_complete_once_every_target_stopped(progress):
    started(progress)
    progress.apply(BenchStart("echo", "a", 1))
    progress.apply(BenchError("echo", "a", 1, Raised(UserError("E", "m"), 0)))
    progress.apply(BenchStart("echo", "b", 1))
    progress.apply(BenchBudgetExceeded("echo", "b", 1, 3_000_000_000))
    assert progress.is_complete()


def test_bye_completes_the_run(progress):
    started(progress).apply(Bye())
    assert progress.is_complete()


def test_a_report_needs_a_hello(progress):
    with pytest.raises(RunnerProtocolError, match="never said hello"):
        progress.report()
