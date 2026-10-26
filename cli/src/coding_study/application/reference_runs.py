"""Running a problem's references and its generated stub in one language (`cstudy verify`)."""

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from coding_study.application.environment import Environment
from coding_study.application.language_runs import CodeRun, LanguageRun, reference_job_id
from coding_study.application.ports import ProgressNotice, References, ReferenceSource
from coding_study.domain import layout
from coding_study.domain.buggy_stubs import BUGGY_STUB_APPROACH_ID, buggy_file
from coding_study.domain.comparators import Comparator
from coding_study.domain.judging import CaseStatus, RunnableCase, judge, outcome_summary
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.problem_files import SOLUTIONS_DIRECTORY
from coding_study.domain.runs import Crashed, NotRun, TimedOut
from coding_study.domain.stress_runs import PlannedRun
from coding_study.domain.stress_verdict import StressVerdict
from coding_study.domain.stub_check import STUB_APPROACH_ID, STUB_DIRECTORY, stub_as_reference

SHOWN_DIAGNOSTICS = 3
SHOWN_FAILURES = 3


@dataclass(frozen=True, slots=True)
class ApproachResult:
    approach_id: str
    failures: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(frozen=True, slots=True)
class StressCheck:
    """One (reference, stress case, variant) of `cstudy verify` D6 or D7."""

    target_id: str
    """The approach id, or the broken reference's id."""
    is_broken: bool
    verdict: StressVerdict
    required_failures: int
    """D7: how many runs must fail; 0 for correct references, which must pass every run."""

    @property
    def ok(self) -> bool:
        if self.is_broken:
            return self.verdict.failed_runs >= self.required_failures
        return self.verdict.status is CaseStatus.PASS


@dataclass(frozen=True, slots=True)
class LanguageResult:
    language: Language
    approaches: tuple[ApproachResult, ...] = ()
    problems: tuple[str, ...] = ()
    """Failures that are not about one approach: the stub, the build."""
    broken: tuple[ApproachResult, ...] = ()
    """Concurrent problems: D7 per broken reference."""
    stress: tuple[StressCheck, ...] = ()
    """Concurrent problems: every stress verdict of D6 and D7."""

    @property
    def passing(self) -> int:
        return sum(1 for approach in self.approaches if approach.passed)

    @property
    def passed(self) -> bool:
        approaches_pass = self.passing == len(self.approaches)
        broken_caught = all(broken.passed for broken in self.broken)
        return not self.problems and approaches_pass and broken_caught


def shown(failures: Sequence[str]) -> tuple[str, ...]:
    """The first few failures, then how many more there are."""
    if len(failures) <= SHOWN_FAILURES:
        return tuple(failures)
    return (*failures[:SHOWN_FAILURES], f"and {len(failures) - SHOWN_FAILURES} more")


def approaches_in(
    environment: Environment, meta: ProblemMeta, language: Language
) -> tuple[str, ...]:
    """Declared approaches with a reference file in `language`, in meta.yaml order."""
    names = set(environment.files.file_names(meta.slug, SOLUTIONS_DIRECTORY))
    return tuple(
        approach.id
        for approach in meta.approaches
        if layout.reference_file_name(approach.id, language) in names
    )


def per_language[T](
    languages: Sequence[Language], work: Callable[[Language], T], jobs: int | None
) -> dict[Language, T]:
    """`work` for every language, at most `jobs` at a time (default: all at once)."""
    if not languages:
        return {}
    with ThreadPoolExecutor(max_workers=jobs or len(languages)) as executor:
        return dict(zip(languages, executor.map(work, languages), strict=True))


class LanguageVerifier:
    def __init__(
        self,
        environment: Environment,
        meta: ProblemMeta,
        language: Language,
        notify: ProgressNotice,
    ) -> None:
        self._environment = environment
        self._meta = meta
        self._language = language
        self._notify = notify
        self._run = LanguageRun(environment, meta, language)

    def references(
        self,
        approach_ids: Sequence[str],
        cases: Sequence[RunnableCase],
        stress: Mapping[str, Sequence[PlannedRun]] | None = None,
    ) -> CodeRun:
        """One build and one runner process for every approach; concurrent problems also run
        each approach's planned stress runs."""
        plans = stress or {}
        jobs = [
            self._run.reference_job(approach_id, cases, plans.get(approach_id, ()))
            for approach_id in approach_ids
        ]
        return self._run.run(self._run.references(approach_ids), jobs, self._notify)

    def stub_problem(self, sample: RunnableCase | None) -> str | None:
        """D1: why the generated stub does not build or load, or None when it does.

        With a `sample` case the stub is also called once; it may throw ("not implemented") but
        must not crash or hang the runner.
        """
        source = self._write_stub()
        scope = References(self._meta, (ReferenceSource(STUB_APPROACH_ID, source),))
        cases = [sample] if sample else []
        result = self._run.run(
            scope, [self._run.reference_job(STUB_APPROACH_ID, cases)], self._notify
        )
        if result.build_failure is not None:
            diagnostics = result.build_failure.diagnostics[:SHOWN_DIAGNOSTICS]
            return "stub does not build: " + " | ".join(diagnostics)
        assert result.report is not None
        job = result.report.job(reference_job_id(self._meta.slug, STUB_APPROACH_ID))
        if job.load_error is not None:
            return f"stub does not load: {job.load_error.type}: {job.load_error.message}"
        broken = (
            report.outcome
            for report in job.cases
            if isinstance(report.outcome, Crashed | TimedOut | NotRun)
        )
        outcome = next(broken, None)
        return f"stub {outcome_summary(outcome)}" if outcome else None

    def buggy_problem(self, cases: Sequence[RunnableCase], comparator: Comparator) -> str | None:
        """D8 for `stub: buggy`: why the buggy file is no debugging exercise, or None when it
        builds, loads and fails at least one case. It replaces the generated-stub check (D1)."""
        source = self._environment.files.path(self._meta.slug, buggy_file(self._language))
        scope = References(self._meta, (ReferenceSource(BUGGY_STUB_APPROACH_ID, source),))
        job = self._run.reference_job(BUGGY_STUB_APPROACH_ID, cases)
        result = self._run.run(scope, [job], self._notify)
        if result.build_failure is not None:
            diagnostics = result.build_failure.diagnostics[:SHOWN_DIAGNOSTICS]
            return "buggy stub does not build: " + " | ".join(diagnostics)
        assert result.report is not None
        report = result.report.job(reference_job_id(self._meta.slug, BUGGY_STUB_APPROACH_ID))
        if report.load_error is not None:
            return (
                f"buggy stub does not load: {report.load_error.type}: {report.load_error.message}"
            )
        verdicts = judge(cases, report, comparator).verdicts
        if all(verdict.status is CaseStatus.PASS for verdict in verdicts):
            return "buggy stub passes every case; it must fail at least one"
        return None

    def _write_stub(self) -> Path:
        stub = self._environment.toolchains.stub_generator(self._language).generate(self._meta)
        name = layout.reference_file_name(STUB_APPROACH_ID, self._language)
        path = f"{STUB_DIRECTORY}/{self._language}/{self._meta.snake_slug}/{name}"
        workspace = self._environment.workspace
        workspace.write_text(path, stub_as_reference(stub, self._language))
        return workspace.absolute(path)
