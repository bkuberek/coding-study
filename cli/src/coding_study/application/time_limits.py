"""Optional time limits for `cstudy test` (docs/specs/performance-analysis.md#time-limits).

A factor limit needs the per-case times of the fastest `optimal` reference in the attempt's
language, measured on this machine through the normal test path and cached in
`.cs/calibration/`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from coding_study.application.case_materialization import CaseMaterializer
from coding_study.application.environment import Environment
from coding_study.application.language_runs import LanguageRun, reference_job_id
from coding_study.application.ports import ProgressNotice
from coding_study.application.reference_runs import approaches_in
from coding_study.domain import layout
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.judging import RunnableCase
from coding_study.domain.precedence import resolve_time_limit, time_limits_enabled
from coding_study.domain.problem import ApproachRole, Language, Problem, ProblemMeta
from coding_study.domain.problem_files import GENERATOR_FILE, TESTS_FILE, solution_file
from coding_study.domain.runs import Returned
from coding_study.domain.time_limits import (
    AbsoluteTimeLimit,
    Calibration,
    TimeLimit,
    TimeLimits,
    fastest_calibration,
    per_case_medians,
)

CALIBRATION_NOTICE = "calibrating time limits (one-time)"
CALIBRATION_RUNS = 3
"""Runner processes per calibration; each case keeps its median time."""


@dataclass(frozen=True, slots=True)
class TimeLimitFlags:
    """`--time-limit[=VALUE]` sets `enabled` (and maybe `value`); `--no-time-limit` clears it."""

    enabled: bool | None = None
    value: TimeLimit | None = None


@dataclass(frozen=True, slots=True)
class TimeLimitRequest:
    problem: Problem
    """Every case of the problem, so one calibration serves any `--case` selection."""
    language: Language
    runtime: str
    """The runner's runtime version from its `hello`; calibrations are only valid for it."""
    flags: TimeLimitFlags


def unavailable_notice(language: Language) -> str:
    return f"time limit unavailable for {language}: no optimal reference"


def resolve_time_limits(
    environment: Environment,
    request: TimeLimitRequest,
    notify: ProgressNotice,
) -> TimeLimits | None:
    """The limits for this run, or None when they are off or cannot apply."""
    config = environment.config
    if not time_limits_enabled(request.flags.enabled, config):
        return None
    meta = request.problem.meta
    limit = resolve_time_limit(request.flags.value, config, meta.perf.time_limit)
    floor_ms = config.time_limit.floor_ms
    if isinstance(limit, AbsoluteTimeLimit):
        return TimeLimits(limit, floor_ms)
    calibration = Calibrator(environment, notify).calibration(request)
    if calibration is None:
        notify(unavailable_notice(request.language))
        return None
    return TimeLimits(limit, floor_ms, calibration)


class Calibrator:
    def __init__(self, environment: Environment, notify: ProgressNotice) -> None:
        self._environment = environment
        self._notify = notify

    def calibration(self, request: TimeLimitRequest) -> Calibration | None:
        """None when the language has no `optimal` reference."""
        meta, language = request.problem.meta, request.language
        approach_ids = _optimal_approaches(self._environment, meta, language)
        if not approach_ids:
            return None
        key = self._key(meta, language, approach_ids, request.runtime)
        cache = self._environment.calibrations
        cached = cache.load(language, meta.slug, key)
        if cached is not None:
            return cached
        self._notify(CALIBRATION_NOTICE)
        calibration = self._measure(request.problem, language, approach_ids)
        if calibration is not None:
            cache.save(language, meta.slug, key, calibration)
        return calibration

    def _key(
        self, meta: ProblemMeta, language: Language, approach_ids: Sequence[str], runtime: str
    ) -> str:
        references = [
            solution_file(layout.reference_file_name(approach_id, language))
            for approach_id in approach_ids
        ]
        names = (*references, TESTS_FILE, GENERATOR_FILE)
        return f"{self._environment.files.fingerprint(meta.slug, names)}:{runtime}"

    def _measure(
        self, problem: Problem, language: Language, approach_ids: Sequence[str]
    ) -> Calibration | None:
        cases = CaseMaterializer(self._environment, self._notify).runnable_cases(problem)
        runs = [
            self._timed_run(problem.meta, language, approach_ids, cases)
            for _ in range(CALIBRATION_RUNS)
        ]
        medians = {
            approach_id: per_case_medians([run[approach_id] for run in runs])
            for approach_id in approach_ids
        }
        return fastest_calibration(medians)

    def _timed_run(
        self,
        meta: ProblemMeta,
        language: Language,
        approach_ids: Sequence[str],
        cases: Sequence[RunnableCase],
    ) -> Mapping[str, Mapping[str, int]]:
        """One runner process for every approach: approach id to case id to `duration_ns`."""
        run = LanguageRun(self._environment, meta, language)
        jobs = [run.reference_job(approach_id, cases) for approach_id in approach_ids]
        result = run.run(run.references(approach_ids), jobs, self._notify)
        if result.report is None:
            raise self._error(meta, language, approach_ids[0], "does not build")
        timings: dict[str, Mapping[str, int]] = {}
        for approach_id in approach_ids:
            job = result.report.job(reference_job_id(meta.slug, approach_id))
            if job.load_error is not None:
                raise self._error(meta, language, approach_id, "does not load")
            timings[approach_id] = {
                report.case_id: report.outcome.duration_ns
                for report in job.cases
                if isinstance(report.outcome, Returned)
            }
        return timings

    def _error(
        self, meta: ProblemMeta, language: Language, approach_id: str, message: str
    ) -> ContentError:
        directory = self._environment.files.problem_directory(meta.slug)
        name = solution_file(layout.reference_file_name(approach_id, language))
        issue = ContentIssue(f"{directory}/{name}", "", f"{message}; time limits need it")
        return ContentError([issue])


def _optimal_approaches(
    environment: Environment, meta: ProblemMeta, language: Language
) -> tuple[str, ...]:
    optimal = {approach.id for approach in meta.approaches if approach.role is ApproachRole.OPTIMAL}
    return tuple(
        approach_id
        for approach_id in approaches_in(environment, meta, language)
        if approach_id in optimal
    )
