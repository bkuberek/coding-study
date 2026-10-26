"""`cstudy verify --conformance`: every runner against runners/conformance/.

Each fixture's reference approaches run in every language the fixture lists and must produce the
outcomes in expectations.json; the generated stub of every fixture must build and load
(docs/specs/runners.md#conformance-suite). Stress cases run `runs` times per variant (default
10), and their expectations bound how many runs fail and how (runners.md#conformance-fixtures-
phase-5).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from coding_study.application.comparison import problem_comparator
from coding_study.application.environment import Environment
from coding_study.application.language_runs import reference_job_id
from coding_study.application.ports import ProgressNotice
from coding_study.application.reference_runs import (
    ApproachResult,
    LanguageResult,
    LanguageVerifier,
    approaches_in,
    per_language,
    shown,
)
from coding_study.domain.comparators import Comparator
from coding_study.domain.concurrency import VERIFY_RUNS
from coding_study.domain.conformance import (
    ConformanceExpectation,
    ConformanceSuite,
    ExpectedStatus,
)
from coding_study.domain.conformance_check import outcome_mismatch, stress_mismatch
from coding_study.domain.errors import ContentError, UnknownProblemError
from coding_study.domain.judging import concrete_case, judge
from coding_study.domain.problem import Language, Problem
from coding_study.domain.runs import JobReport, RunReport
from coding_study.domain.stress import StressScenario
from coding_study.domain.stress_runs import CaseRuns, PlannedRun, stress_cases
from coding_study.domain.stress_verdict import StressJudging, judge_stress


@dataclass(frozen=True, slots=True)
class ConformanceRequest:
    slugs: tuple[str, ...] = ()
    """Empty: every fixture."""
    language: Language | None = None
    jobs: int | None = None


@dataclass(frozen=True, slots=True)
class FixtureVerification:
    directory: str
    languages: tuple[LanguageResult, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.errors and all(language.passed for language in self.languages)


def verify_conformance(
    environment: Environment,
    suite: ConformanceSuite,
    request: ConformanceRequest,
    notify: ProgressNotice,
) -> tuple[FixtureVerification, ...]:
    """`environment` reads the fixtures (see `conformance_environment`)."""
    fixtures = environment.files.slugs()
    for slug in request.slugs:
        if slug not in fixtures:
            raise UnknownProblemError(slug)
    selected = request.slugs or fixtures
    results = [_Fixture(environment, suite, request, notify).verify(slug) for slug in selected]
    orphans = {
        expectation.slug
        for expectation in suite.expectations
        if expectation.slug not in fixtures
        and (not request.slugs or expectation.slug in request.slugs)
    }
    results += [
        FixtureVerification(
            f"{suite.problems_directory}/{slug}",
            errors=(f'expectations.json names "{slug}", which has no fixture',),
        )
        for slug in sorted(orphans)
    ]
    return tuple(results)


class _Fixture:
    def __init__(
        self,
        environment: Environment,
        suite: ConformanceSuite,
        request: ConformanceRequest,
        notify: ProgressNotice,
    ) -> None:
        self._environment = environment
        self._suite = suite
        self._request = request
        self._notify = notify

    def verify(self, slug: str) -> FixtureVerification:
        directory = self._environment.files.problem_directory(slug)
        try:
            problem = self._environment.problems.load(slug)
            comparator = problem_comparator(self._environment, problem.meta)
        except ContentError as error:
            return FixtureVerification(directory, errors=tuple(map(str, error.issues)))
        expectations = tuple(
            expectation for expectation in self._suite.expectations if expectation.slug == slug
        )
        languages = [
            language
            for language in problem.meta.languages
            if self._request.language in (None, language)
        ]
        run = _FixtureRun(self._environment, problem, comparator, self._notify)
        results = per_language(
            languages, lambda language: run.language(language, expectations), self._request.jobs
        )
        return FixtureVerification(directory, tuple(results.values()))


class _FixtureRun:
    def __init__(
        self,
        environment: Environment,
        problem: Problem,
        comparator: Comparator,
        notify: ProgressNotice,
    ) -> None:
        self._environment = environment
        self._problem = problem
        self._comparator = comparator
        self._notify = notify
        self._cases = tuple(
            concrete_case(case)
            for case in problem.cases
            if not isinstance(case.input, StressScenario)
        )

    def language(
        self, language: Language, expectations: Sequence[ConformanceExpectation]
    ) -> LanguageResult:
        meta = self._problem.meta
        verifier = LanguageVerifier(self._environment, meta, language, self._notify)
        stub = verifier.stub_problem(self._cases[0] if self._cases else None)
        problems = [stub] if stub else []
        available = set(approaches_in(self._environment, meta, language))
        present = [item for item in expectations if item.approach_id in available]
        problems += [
            f"no {language} reference for {item.approach_id}"
            for item in expectations
            if item.approach_id not in available
        ]
        if not present:
            return LanguageResult(language, (), tuple(problems))
        plans = {item.approach_id: self._plan(item, language) for item in present}
        code_run = verifier.references([item.approach_id for item in present], self._cases, plans)
        if code_run.report is None:
            diagnostics = code_run.build_failure.diagnostics if code_run.build_failure else ()
            problems.append("references do not build: " + " | ".join(diagnostics[:3]))
            unbuilt = tuple(ApproachResult(item.approach_id, ("not built",)) for item in present)
            return LanguageResult(language, unbuilt, tuple(problems))
        results = tuple(
            self._approach(item, code_run.report, plans[item.approach_id]) for item in present
        )
        return LanguageResult(language, results, tuple(problems))

    def _plan(
        self, expectation: ConformanceExpectation, language: Language
    ) -> tuple[PlannedRun, ...]:
        """Each stress case `runs` times per variant; a `deterministic` case repeats its first
        seed once more at the end, so two runs share a seed."""
        concurrency = self._problem.meta.concurrency
        if concurrency is None:
            return ()
        planned: list[PlannedRun] = []
        for case in stress_cases(self._problem):
            assert isinstance(case.input, StressScenario)
            outcome = expectation.outcome_for(case.id)
            seeds = [case.input.seed + run for run in range(outcome.runs or VERIFY_RUNS)]
            if outcome.deterministic:
                seeds.append(seeds[0])
            for variant in concurrency.variants(language):
                planned += CaseRuns(case, concurrency, language, variant).plan(seeds)
        return tuple(planned)

    def _approach(
        self,
        expectation: ConformanceExpectation,
        report: RunReport,
        planned: Sequence[PlannedRun],
    ) -> ApproachResult:
        approach = expectation.approach_id
        mismatches = self._mismatches(expectation, report)
        job = report.job(reference_job_id(self._problem.meta.slug, approach))
        if planned and job.load_error is None:
            mismatches += self._stress_mismatches(expectation, job, planned)
        return ApproachResult(approach, shown(mismatches))

    def _stress_mismatches(
        self, expectation: ConformanceExpectation, job: JobReport, planned: Sequence[PlannedRun]
    ) -> list[str]:
        verdicts = judge_stress(planned, job, StressJudging(self._comparator))
        return [
            mismatch
            for verdict in verdicts
            if (
                mismatch := stress_mismatch(
                    expectation.outcome_for(verdict.case_id), verdict, job.restarted_after
                )
            )
        ]

    def _mismatches(self, expectation: ConformanceExpectation, report: RunReport) -> list[str]:
        job = report.job(reference_job_id(self._problem.meta.slug, expectation.approach_id))
        expects_load_error = expectation.outcome.status is ExpectedStatus.LOAD_ERROR
        if job.load_error is not None:
            if expects_load_error:
                return []
            return [f"unexpected load_error: {job.load_error.type}: {job.load_error.message}"]
        if expects_load_error:
            return ["expected load_error, but the target loaded"]
        judgement = judge(self._cases, job, self._comparator)
        return [
            f"{verdict.case.id}: {mismatch}"
            for verdict in judgement.verdicts
            if (mismatch := outcome_mismatch(expectation.outcome_for(verdict.case.id), verdict))
        ]
