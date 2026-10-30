"""`cstudy verify` D6 and D7 for concurrent problems (docs/specs/authoring.md#dynamic).

D6: every approach passes every sequential case and every stress case in N of N runs per variant.
D7: every broken reference passes every sequential case and fails each of its `caught_by` cases in
at least `ceil(0.9 * N)` runs per language and variant. All of a language's references and broken
references share one build and one runner process. The languages build side by side, but their
runners take turns (`runner_slot`): a stress run measures one runner alone, as a user's run does,
not the contention of every language's workers at once, which hid races and stretched runs.
"""

import math
from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.language_runs import LanguageRun, reference_job_id
from coding_study.application.ports import ProgressNotice, References
from coding_study.application.reference_runs import (
    SHOWN_DIAGNOSTICS,
    ApproachResult,
    StressCheck,
    shown,
)
from coding_study.application.stress_judging import stress_judging
from coding_study.domain import layout
from coding_study.domain.comparators import Comparator
from coding_study.domain.concurrency import VERIFY_RUNS, BrokenReference
from coding_study.domain.judging import CaseStatus, RunnableCase, judge, verdict_summary
from coding_study.domain.problem import Language, Problem
from coding_study.domain.problem_files import BROKEN_DIRECTORY
from coding_study.domain.runs import JobReport, RunReport
from coding_study.domain.stress_runs import PlannedRun, StressSelection, plan_runs
from coding_study.domain.stress_verdict import StressJudging, StressVerdict, judge_stress

DETECTION_SHARE = 0.9
"""D7: a broken reference must fail a `caught_by` case in at least this share of runs."""


def required_failures(runs: int) -> int:
    return math.ceil(DETECTION_SHARE * runs)


@dataclass(frozen=True, slots=True)
class ConcurrentLanguageResult:
    approaches: tuple[ApproachResult, ...]
    broken: tuple[ApproachResult, ...]
    stress: tuple[StressCheck, ...]
    problems: tuple[str, ...] = ()


class ConcurrentVerifier:
    """One language of one concurrent problem."""

    def __init__(
        self,
        environment: Environment,
        problem: Problem,
        language: Language,
        notify: ProgressNotice,
        runner_slot: AbstractContextManager[object] | None = None,
    ) -> None:
        """`runner_slot`, shared by the problem's languages, is held while the runner runs."""
        self._environment = environment
        self._problem = problem
        self._meta = problem.meta
        self._language = language
        self._notify = notify
        self._runner_slot = runner_slot
        self._run = LanguageRun(environment, problem.meta, language)

    def verify(
        self,
        approach_ids: Sequence[str],
        cases: Sequence[RunnableCase],
        comparator: Comparator,
        runs: int | None,
    ) -> ConcurrentLanguageResult:
        brokens = self._brokens()
        selection = StressSelection(runs=runs or VERIFY_RUNS)
        plans = {
            approach: plan_runs(self._problem, self._language, selection)
            for approach in approach_ids
        }
        plans |= {
            broken.approach_id: plan_runs(self._caught_by(broken), self._language, selection)
            for broken in brokens
        }
        jobs = [
            self._run.reference_job(target, cases, plans[target])
            for target in (*approach_ids, *(broken.approach_id for broken in brokens))
        ]
        sources = (
            *self._run.references(approach_ids).sources,
            *self._run.broken_references(brokens),
        )
        scope = References(self._meta, sources)
        code_run = self._run.run(scope, jobs, self._notify, self._runner_slot)
        if code_run.report is None:
            diagnostics = code_run.build_failure.diagnostics if code_run.build_failure else ()
            problem = "references do not build: " + " | ".join(diagnostics[:SHOWN_DIAGNOSTICS])
            unbuilt = tuple(ApproachResult(approach, ("not built",)) for approach in approach_ids)
            return ConcurrentLanguageResult(unbuilt, (), (), (problem,))
        judging = stress_judging(self._environment, self._problem, comparator)
        checks = _Checks(code_run.report, cases, comparator, judging, self._meta.slug)
        approaches = tuple(checks.approach(approach, plans[approach]) for approach in approach_ids)
        broken_results = tuple(
            checks.broken(broken, plans[broken.approach_id]) for broken in brokens
        )
        return ConcurrentLanguageResult(approaches, broken_results, checks.stress_checks)

    def _brokens(self) -> tuple[BrokenReference, ...]:
        concurrency = self._meta.concurrency
        if concurrency is None:
            return ()
        names = set(self._environment.files.file_names(self._meta.slug, BROKEN_DIRECTORY))
        return tuple(
            broken
            for broken in concurrency.broken
            if broken.covers(self._language, self._meta.languages)
            and layout.reference_file_name(broken.id, self._language) in names
        )

    def _caught_by(self, broken: BrokenReference) -> Problem:
        cases = tuple(case for case in self._problem.cases if case.id in broken.caught_by)
        return replace(self._problem, cases=cases)


class _Checks:
    def __init__(
        self,
        report: RunReport,
        cases: Sequence[RunnableCase],
        comparator: Comparator,
        judging: StressJudging,
        slug: str,
    ) -> None:
        self._report = report
        self._cases = cases
        self._comparator = comparator
        self._judging = judging
        self._slug = slug
        self.stress_checks: tuple[StressCheck, ...] = ()

    def approach(self, approach: str, planned: Sequence[PlannedRun]) -> ApproachResult:
        job = self._report.job(reference_job_id(self._slug, approach))
        failures = self._sequential(job)
        if job.load_error is None:
            for verdict in self._verdicts(planned, job):
                check = StressCheck(approach, False, verdict, 0)
                self.stress_checks += (check,)
                if not check.ok:
                    failures.append(_stress_failure(verdict))
        return ApproachResult(approach, shown(failures))

    def broken(self, broken: BrokenReference, planned: Sequence[PlannedRun]) -> ApproachResult:
        job = self._report.job(reference_job_id(self._slug, broken.approach_id))
        failures = [f"sequential {failure}" for failure in self._sequential(job)]
        if job.load_error is None:
            for verdict in self._verdicts(planned, job):
                needed = required_failures(len(verdict.runs))
                check = StressCheck(broken.id, True, verdict, needed)
                self.stress_checks += (check,)
                if not check.ok:
                    failures.append(
                        f"{verdict.case_id} {verdict.variant} caught in {verdict.failed_runs}"
                        f"/{len(verdict.runs)} runs (needs {needed})"
                    )
        return ApproachResult(broken.id, shown(failures))

    def _sequential(self, job: JobReport) -> list[str]:
        if job.load_error is not None:
            error = job.load_error
            return [f"does not load: {error.type}: {error.message}"]
        judgement = judge(self._cases, job, self._comparator)
        return [
            verdict_summary(verdict)
            for verdict in judgement.verdicts
            if verdict.status is not CaseStatus.PASS
        ]

    def _verdicts(self, planned: Sequence[PlannedRun], job: JobReport) -> tuple[StressVerdict, ...]:
        return judge_stress(planned, job, self._judging)


def _stress_failure(verdict: StressVerdict) -> str:
    """`s1 virtual 7/10 runs passed; run 3 seed 1003: <reason>`."""
    passed = f"{verdict.runs_passed}/{len(verdict.runs)} runs passed"
    head = f"{verdict.case_id} {verdict.variant} {passed}"
    first = verdict.failures[0] if verdict.failures else None
    if first is None:
        return head
    reason = first.reasons[0] if first.reasons else first.status.value
    return f"{head}; run {first.run} seed {first.seed}: {reason}"
