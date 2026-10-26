"""Optional time limits in `cstudy test` (docs/specs/performance-analysis.md#time-limits)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.run_tests import RunTestsRequest, run_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.time_limits import (
    CALIBRATION_NOTICE,
    TimeLimitFlags,
)
from coding_study.domain.attempts import RunRecord
from coding_study.domain.config import Config, TimeLimitSettings
from coding_study.domain.judging import CaseStatus
from coding_study.domain.problem import Language
from coding_study.domain.runs import Returned, RunCase, RunJob, UserError
from coding_study.domain.time_limits import AbsoluteTimeLimit, FactorTimeLimit
from tests.fakes import (
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    two_sum,
)
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
MS = 1_000_000
REFERENCE_NS = 1 * MS
ON = TimeLimitFlags(enabled=True)
SMALL_FLOOR = Config(time_limit=TimeLimitSettings(floor_ms=1))
"""With a 1 ms floor the default 5x limit of the 1 ms reference is 5 ms per case."""


def taking(user_ns: int):
    """Correct answers; the user's calls take `user_ns`, every reference call REFERENCE_NS."""

    def answer(job: RunJob, case: RunCase) -> Returned:
        duration = user_ns if job.job_id == "two-sum" else REFERENCE_NS
        return replace(two_sum(job, case), duration_ns=duration)

    return answer


def environment_for(tmp_path, user_ns: int, config: Config = SMALL_FLOOR, language=Language.PYTHON):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner(), Language.KOTLIN: FakeLanguageRunner()},
        {Language.PYTHON: FakeStubGenerator(), Language.KOTLIN: FakeStubGenerator()},
    )
    process = ScriptedRunnerProcess(taking(user_ns))
    environment = make_environment(
        root, toolchains=toolchains, runner_process=process, config=config
    )
    start_attempt(environment, StartRequest("two-sum", language))
    return environment


def run(environment, flags: TimeLimitFlags = ON, notices: list[str] | None = None, **fields):
    request = RunTestsRequest(time_limits=flags, **fields)
    return run_tests(environment, request, (notices if notices is not None else []).append)


def calibration_runs(environment) -> int:
    """Runner processes that ran the optimal reference on a hand-written case."""
    return sum(
        1
        for request in environment.runner_process.requests
        for job in request.jobs
        if job.job_id == "two-sum/hash-map" and any(case.id == "ex1" for case in job.cases)
    )


def stored_run(environment, result) -> RunRecord:
    stored = environment.progress.latest_test_run(result.attempt.id)
    assert stored is not None
    return stored


def statuses(result) -> list[CaseStatus]:
    return [verdict.status for verdict in result.judgement.verdicts]


def test_time_limits_are_off_by_default(tmp_path):
    environment = environment_for(tmp_path, user_ns=10_000 * MS)
    assert run(environment, TimeLimitFlags()).time_limits is None


def test_slow_code_passes_while_time_limits_are_off(tmp_path):
    environment = environment_for(tmp_path, user_ns=10_000 * MS)
    assert run(environment, TimeLimitFlags()).passed


def test_flag_applies_the_built_in_factor(tmp_path):
    limits = run(environment_for(tmp_path, user_ns=MS)).time_limits
    assert limits is not None
    assert limits.limit == FactorTimeLimit(5)


def test_case_slower_than_its_limit_is_tle(tmp_path):
    result = run(environment_for(tmp_path, user_ns=6 * MS))
    assert statuses(result) == [CaseStatus.TLE] * 4


def test_case_within_its_limit_passes(tmp_path):
    assert run(environment_for(tmp_path, user_ns=4 * MS)).passed


def test_floor_keeps_tiny_cases_from_failing(tmp_path):
    environment = environment_for(tmp_path, user_ns=6 * MS, config=Config())
    assert run(environment).passed


def test_config_enables_time_limits(tmp_path):
    config = Config(time_limit=TimeLimitSettings(enabled=True, floor_ms=1))
    result = run(environment_for(tmp_path, user_ns=6 * MS, config=config), TimeLimitFlags())
    assert not result.passed


def test_no_time_limit_flag_wins_over_config(tmp_path):
    config = Config(time_limit=TimeLimitSettings(enabled=True, floor_ms=1))
    environment = environment_for(tmp_path, user_ns=6 * MS, config=config)
    assert run(environment, TimeLimitFlags(enabled=False)).time_limits is None


def test_flag_value_wins_over_config_and_meta(tmp_path):
    config = Config(time_limit=TimeLimitSettings(value=FactorTimeLimit(100), floor_ms=1))
    environment = environment_for(tmp_path, user_ns=4 * MS, config=config)
    result = run(environment, TimeLimitFlags(enabled=True, value=AbsoluteTimeLimit(3)))
    assert statuses(result) == [CaseStatus.TLE] * 4


def test_config_value_wins_over_the_built_in_factor(tmp_path):
    config = Config(time_limit=TimeLimitSettings(value=FactorTimeLimit(10), floor_ms=1))
    assert run(environment_for(tmp_path, user_ns=6 * MS, config=config)).passed


def test_meta_suggestion_is_used_when_flag_and_config_give_no_value(tmp_path):
    environment = environment_for(tmp_path, user_ns=6 * MS)
    meta = environment.root / "problems" / "0001-two-sum" / "meta.yaml"
    meta.write_text(
        meta.read_text().replace(
            "  expected_from: hash-map\n", "  expected_from: hash-map\n  time_limit: {factor: 10}\n"
        )
    )
    assert run(environment).passed


def test_absolute_limit_needs_no_calibration(tmp_path):
    environment = environment_for(tmp_path, user_ns=MS)
    run(environment, TimeLimitFlags(enabled=True, value=AbsoluteTimeLimit(50)))
    assert calibration_runs(environment) == 0


def test_calibration_runs_the_optimal_reference_in_three_processes(tmp_path):
    environment = environment_for(tmp_path, user_ns=MS)
    run(environment)
    assert calibration_runs(environment) == 3


def test_calibration_is_cached(tmp_path):
    environment = environment_for(tmp_path, user_ns=MS)
    run(environment)
    run(environment)
    assert calibration_runs(environment) == 3


def test_first_calibration_is_announced(tmp_path):
    notices: list[str] = []
    run(environment_for(tmp_path, user_ns=MS), notices=notices)
    assert CALIBRATION_NOTICE in notices


def test_cached_calibration_is_not_announced(tmp_path):
    environment = environment_for(tmp_path, user_ns=MS)
    run(environment)
    notices: list[str] = []
    run(environment, notices=notices)
    assert CALIBRATION_NOTICE not in notices


def test_changed_reference_is_calibrated_again(tmp_path):
    environment = environment_for(tmp_path, user_ns=MS)
    run(environment)
    reference = environment.root / "problems" / "0001-two-sum" / "solutions" / "hash-map.py"
    reference.write_text(reference.read_text() + "\n# changed\n")
    run(environment)
    assert calibration_runs(environment) == 6


def test_selected_cases_are_limited_by_the_full_calibration(tmp_path):
    environment = environment_for(tmp_path, user_ns=6 * MS)
    assert statuses(run(environment, case_ids=("g1",))) == [CaseStatus.TLE]


def test_language_without_an_optimal_reference_runs_without_limits(tmp_path):
    environment = environment_for(tmp_path, user_ns=6 * MS, language=Language.KOTLIN)
    assert run(environment).time_limits is None


def test_missing_optimal_reference_is_explained(tmp_path):
    notices: list[str] = []
    run(environment_for(tmp_path, user_ns=MS, language=Language.KOTLIN), notices=notices)
    assert "time limit unavailable for kotlin: no optimal reference" in notices


def test_absolute_limit_applies_without_a_reference(tmp_path):
    environment = environment_for(tmp_path, user_ns=6 * MS, language=Language.KOTLIN)
    flags = TimeLimitFlags(enabled=True, value=AbsoluteTimeLimit(5))
    assert statuses(run(environment, flags)) == [CaseStatus.TLE] * 4


@pytest.mark.parametrize(
    ("flags", "stored"),
    [(ON, "5x"), (TimeLimitFlags(enabled=True, value=AbsoluteTimeLimit(1500)), "1500ms")],
)
def test_run_records_the_time_limit(tmp_path, flags, stored):
    environment = environment_for(tmp_path, user_ns=MS)
    result = run(environment, flags)
    assert stored_run(environment, result).time_limit == stored


def test_run_without_time_limits_records_none(tmp_path):
    environment = environment_for(tmp_path, user_ns=MS)
    result = run(environment, TimeLimitFlags())
    assert stored_run(environment, result).time_limit is None


def test_tle_cases_are_counted_in_the_stored_tally(tmp_path):
    environment = environment_for(tmp_path, user_ns=6 * MS)
    result = run(environment)
    assert stored_run(environment, result).tally.tle == 4


def test_code_that_does_not_load_is_not_timed(tmp_path):
    environment = environment_for(tmp_path, user_ns=MS)
    process = environment.runner_process
    assert isinstance(process, ScriptedRunnerProcess)
    process.load_errors["two-sum"] = UserError("ImportError", "boom")
    run(environment)
    assert calibration_runs(environment) == 0
