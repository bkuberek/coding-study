"""`SubprocessRunner.bench` driving the real Python runner (runners/python), started with the
CLI's own interpreter: fast enough for the default suite, and it proves both ends of the
bench protocol fit together."""

import sys
import textwrap
from pathlib import Path

import pytest

from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import RunnerLaunch
from coding_study.domain.bench_runs import (
    BenchInput,
    BenchJob,
    BenchReport,
    BenchRequest,
    BenchSettings,
    BenchTarget,
    Warmup,
)
from coding_study.domain.cases import FunctionInput
from coding_study.domain.naming import FunctionNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import Crashed, FileTarget, Raised
from coding_study.domain.signature import FunctionSignature, Param, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType
from tests.helpers import REPOSITORY_ROOT

RUNNER_SOURCES = REPOSITORY_ROOT / "runners" / "python" / "src"
BOOTSTRAP = (
    f"import sys; sys.path.insert(0, {str(RUNNER_SOURCES)!r}); "
    "from cs_runner.program import main; sys.exit(main(sys.argv[1:]))"
)
LAUNCH = RunnerLaunch((sys.executable, "-c", BOOTSTRAP), REPOSITORY_ROOT, 5_000)
INT = ScalarType(Scalar.INT)
ECHO = FunctionSignature("echo", (Param("value", INT),), Returns(INT))
NAMES = FunctionNames("echo", {"value": "value"})
SETTINGS = BenchSettings(2, Warmup(1, 1, 0.05), 2000, True, 0)
HANG_GUARD_MS = 250
SIZES = (1, 2, 3, 4)

ECHO_SOURCE = """
def echo(value):
    return value
"""
HANGS_AT_THREE = """
import time


def echo(value):
    if value == 3:
        time.sleep(60)
    return value
"""
CRASHES_AT_THREE = """
import os


def echo(value):
    if value == 3:
        os._exit(9)
    return value
"""
RAISES_AT_TWO = """
def echo(value):
    if value == 2:
        raise ValueError("two")
    return value
"""
SLOW_AT_FOUR = """
import time


def echo(value):
    if value == 4:
        time.sleep(0.05)
    return value
"""


def target(directory: Path, target_id: str, source: str, emits_output: bool = False) -> BenchTarget:
    path = directory / f"{target_id}.py"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return BenchTarget(target_id, FileTarget(str(path)), NAMES, emits_output)


def bench(tmp_path: Path, *targets: BenchTarget, budget_ms: int = 2000) -> BenchReport:
    job = BenchJob(
        job_id="echo",
        kind=ProblemKind.FUNCTION,
        signature=ECHO,
        targets=targets,
        inputs=tuple(BenchInput(size, FunctionInput({"value": size}), 1) for size in SIZES),
        settings=BenchSettings(2, Warmup(1, 1, 0.05), budget_ms, True, 0),
        hang_guard_ms=HANG_GUARD_MS,
    )
    return SubprocessRunner(tmp_path / "runs").bench(LAUNCH, BenchRequest(job))


def sizes_reached(report: BenchReport, target_id: str) -> list[int]:
    return [measured.size for measured in report.target(target_id).sizes if measured.samples]


@pytest.fixture
def steady(tmp_path):
    return target(tmp_path, "steady", ECHO_SOURCE)


@pytest.fixture(scope="module")
def hang_report(tmp_path_factory: pytest.TempPathFactory) -> BenchReport:
    """One bench shared by the hang tests: a hang costs the hang guard plus a restart."""
    directory = tmp_path_factory.mktemp("hang")
    hangs = target(directory, "hangs", HANGS_AT_THREE)
    return bench(directory, hangs, target(directory, "steady", ECHO_SOURCE))


@pytest.fixture(scope="module")
def crash_report(tmp_path_factory: pytest.TempPathFactory) -> BenchReport:
    directory = tmp_path_factory.mktemp("crash")
    crashes = target(directory, "crashes", CRASHES_AT_THREE)
    return bench(directory, crashes, target(directory, "steady", ECHO_SOURCE))


def test_the_report_names_the_runner(tmp_path, steady):
    assert bench(tmp_path, steady).runner.runner == "python"


def test_every_size_gets_one_sample_per_rep(tmp_path, steady):
    report = bench(tmp_path, steady)
    assert [len(measured.samples) for measured in report.target("steady").sizes] == [2, 2, 2, 2]


def test_memory_is_recorded_per_size(tmp_path, steady):
    measured = bench(tmp_path, steady).target("steady").sizes[0]
    assert measured.memory is not None
    assert measured.memory.metric == "tracemalloc_peak"


def test_output_targets_record_their_output(tmp_path):
    report = bench(tmp_path, target(tmp_path, "user", ECHO_SOURCE, emits_output=True))
    outputs = [measured.output.value for measured in report.target("user").sizes if measured.output]
    assert outputs == list(SIZES)


def test_a_hang_counts_as_a_call_over_the_hang_guard(hang_report):
    measured = hang_report.target("hangs").at(3)
    assert measured is not None
    assert measured.exceeded_ns == HANG_GUARD_MS * 1_000_000


def test_the_other_targets_reach_every_size_after_a_hang(hang_report):
    assert sizes_reached(hang_report, "steady") == list(SIZES)


def test_sizes_measured_again_after_a_restart_are_not_counted_twice(hang_report):
    measured = hang_report.target("steady").at(3)
    assert measured is not None
    assert len(measured.samples) == 2


def test_a_hang_is_noted(hang_report):
    assert hang_report.notes == (f"hangs ran over {HANG_GUARD_MS} ms at n=3",)


def test_a_crash_is_a_failure_of_the_target_in_progress(crash_report):
    measured = crash_report.target("crashes").at(3)
    assert measured is not None
    assert isinstance(measured.failure, Crashed)


def test_the_other_targets_reach_every_size_after_a_crash(crash_report):
    assert sizes_reached(crash_report, "steady") == list(SIZES)


def test_an_exception_is_a_failure_at_its_size(tmp_path):
    report = bench(tmp_path, target(tmp_path, "raises", RAISES_AT_TWO))
    measured = report.target("raises").at(2)
    assert measured is not None
    assert isinstance(measured.failure, Raised)


def test_a_failed_target_stops(tmp_path):
    report = bench(tmp_path, target(tmp_path, "raises", RAISES_AT_TWO))
    assert [measured.size for measured in report.target("raises").sizes] == [1, 2]


def test_a_call_over_the_budget_is_recorded(tmp_path):
    report = bench(tmp_path, target(tmp_path, "slow", SLOW_AT_FOUR), budget_ms=20)
    measured = report.target("slow").at(4)
    assert measured is not None
    assert measured.exceeded_ns is not None


def test_a_target_that_does_not_load_has_a_load_error(tmp_path, steady):
    missing = BenchTarget("missing", FileTarget(str(tmp_path / "missing.py")), NAMES)
    load_error = bench(tmp_path, missing, steady).target("missing").load_error
    assert load_error is not None
    assert load_error.type == "FileNotFoundError"
