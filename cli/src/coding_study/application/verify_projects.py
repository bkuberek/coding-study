"""`cstudy verify` on a project problem: D1, D3, D6, D7, D9 and D10
(docs/specs/authoring.md#dynamic).

D1: the starter, copied with level 1's generated tests as `cstudy start` seeds a folder, loads: a
grading job of level 1 reports every case without a load error (the cases may fail), and its
native suite runs to its end without crashing the runner. D3: the reference, the starter with its
overlay and the generated tests of every level (docs/specs/runners.md#reference-materialization),
passes every case of every level. D6, for a project with stress cases: the same grading job runs
every stress case N times (10, or `--stress N`) per variant, and every run passes. D7: each broken
overlay, built on the starter and the reference's overlay, passes every sequential case and fails
each of its `caught_by` stress cases in at least `ceil(0.9 * N)` runs. D9: the reference passes its
native suite. D10, for a project on the virtual clock: the reference is graded again and again,
without its stress cases, and every case gives the same outputs in every run, within a quarter of
its hang guard. Every job gets a runner of its own (docs/specs/runners.md#project-jobs).
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from coding_study.application.environment import Environment
from coding_study.application.jdk_requirement import release_of_content
from coding_study.application.ports import ProgressNotice
from coding_study.application.project_runs import (
    COMPILE_ERROR,
    GradingRun,
    SuiteRun,
    grading_stress_plan,
    run_grading,
    run_suite,
)
from coding_study.application.reference_runs import (
    ApproachResult,
    LanguageResult,
    StressCheck,
    shown,
)
from coding_study.application.verify_concurrency import required_failures, stress_failure
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.clock_determinism import (
    DETERMINISM_RUNS,
    DeterminismVerdict,
    judge_determinism,
)
from coding_study.domain.concurrency import BROKEN_PREFIX, VERIFY_RUNS, BrokenReference
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.judging import Judgement, outcome_summary, verdict_summary
from coding_study.domain.layout import BUILD_DIRECTORY
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import Language, Problem
from coding_study.domain.problem_files import (
    BROKEN_DIRECTORY,
    SOLUTIONS_DIRECTORY,
    STARTER_DIRECTORY,
)
from coding_study.domain.project import (
    NO_PROJECT_FILES,
    ProjectTree,
    project_language,
)
from coding_study.domain.project_tests import level_tests
from coding_study.domain.runs import Crashed, NotRun, Raised, TimedOut, UserError
from coding_study.domain.service_project import service_of
from coding_study.domain.stress import StressScenario
from coding_study.domain.stress_runs import PlannedRun, StressSelection
from coding_study.domain.stub_check import STUB_DIRECTORY
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Passed,
    Skipped,
    SuiteOutcome,
    SuiteReport,
    SuiteTest,
)
from coding_study.domain.virtual_clock import ProjectClock

PROJECT_BUILDS = f"{BUILD_DIRECTORY}/projects"
"""A reference's build: `<PROJECT_BUILDS>/<slug>/<approach>/`."""
STARTER_BUILDS = f"{STUB_DIRECTORY}/projects"
"""D1's copy of a starter: `<STARTER_BUILDS>/<slug>/`, next to the generated stubs it replaces."""
STARTER_SUITE = "starter suite"
NOT_RUN = "not run: the reference does not build"
NOT_TEXT = "is not UTF-8 text: a project holds text files only"
_NO_FILES = ProjectTree(())


@dataclass(frozen=True, slots=True)
class SuiteCheck:
    """D9: the reference's native suite."""

    passing: int
    """Tests that passed or were skipped."""
    total: int
    """Tests the suite reported."""
    failures: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(frozen=True, slots=True)
class ProjectVerification:
    language: LanguageResult
    """D3 as the project's one approach; D1 as the language's problems."""
    suite: SuiteCheck
    determinism: DeterminismVerdict | None = None
    """D10; None for a project on the real clock, and when the reference did not run."""


def verify_project(
    environment: Environment,
    problem: Problem,
    language: Language,
    notify: ProgressNotice,
    stress_runs: int | None = None,
) -> ProjectVerification:
    """D1, D3, D9, D6 and D7 with stress cases (`stress_runs` per stress case and variant, default
    10), and D10 on the virtual clock, in `language`, the problem's one language.

    Raises LanguageNotSetUpError without a test generator for the language, RunnerStartError
    when its runner cannot run project jobs, and ContentError for a project file that is not text
    or a broken stress_checker.py.
    """
    selection = StressSelection(runs=stress_runs or VERIFY_RUNS)
    return _ProjectChecks(environment, problem, language, notify, selection).verify()


def reference_build(environment: Environment, problem: Problem, approach_id: str) -> Path:
    """The approach's build: the starter, its overlay over it, then the generated test file of
    every level, in a folder synced to exactly those files; returns the absolute root."""
    files = problem.project_files or NO_PROJECT_FILES
    trees = {
        STARTER_DIRECTORY: files.starter or _NO_FILES,
        f"{SOLUTIONS_DIRECTORY}/{approach_id}": files.overlays.get(approach_id, _NO_FILES),
    }
    folder = reference_folder(problem, approach_id)
    return _ProjectBuild(environment, problem).write(folder, trees, last_level(problem))


def reference_folder(problem: Problem, approach_id: str) -> str:
    """Where `reference_build` writes, relative to the workspace."""
    return f"{PROJECT_BUILDS}/{problem.meta.slug}/{approach_id}"


def broken_build(environment: Environment, problem: Problem, broken_id: str) -> Path:
    """A broken overlay's build: the starter, the reference's overlay over it, the broken overlay
    over both, then the generated test file of every level, in
    `<PROJECT_BUILDS>/<slug>/broken-<id>/` (docs/specs/problem-format.md#stress-cases-in-
    projects); returns the absolute root."""
    files = problem.project_files or NO_PROJECT_FILES
    reference = problem.meta.approaches[0].id if problem.meta.approaches else ""
    trees = {
        STARTER_DIRECTORY: files.starter or _NO_FILES,
        f"{SOLUTIONS_DIRECTORY}/{reference}": files.overlays.get(reference, _NO_FILES),
        f"{BROKEN_DIRECTORY}/{broken_id}": files.broken.get(broken_id, _NO_FILES),
    }
    folder = f"{PROJECT_BUILDS}/{problem.meta.slug}/{BROKEN_PREFIX}{broken_id}"
    return _ProjectBuild(environment, problem).write(folder, trees, last_level(problem))


def project_brokens(problem: Problem) -> tuple[BrokenReference, ...]:
    """The broken references whose overlay holds at least one file, in meta.yaml order."""
    concurrency = problem.meta.concurrency
    broken = (problem.project_files or NO_PROJECT_FILES).broken
    if concurrency is None:
        return ()
    return tuple(found for found in concurrency.broken if broken.get(found.id, _NO_FILES).files)


def starter_build(environment: Environment, problem: Problem) -> Path:
    """The starter with level 1's generated test file, as `cstudy start` seeds a project folder,
    in a folder synced to exactly those files; returns the absolute root."""
    starter = (problem.project_files or NO_PROJECT_FILES).starter or _NO_FILES
    folder = f"{STARTER_BUILDS}/{problem.meta.slug}"
    trees = {STARTER_DIRECTORY: starter}
    return _ProjectBuild(environment, problem).write(folder, trees, FIRST_LEVEL)


def project_approaches(problem: Problem) -> tuple[str, ...]:
    """Declared approaches whose overlay holds at least one file, in meta.yaml order."""
    overlays = (problem.project_files or NO_PROJECT_FILES).overlays
    return tuple(
        approach.id
        for approach in problem.meta.approaches
        if approach.id in overlays and overlays[approach.id].files
    )


def last_level(problem: Problem) -> int:
    return max((level.number for level in problem.meta.levels), default=FIRST_LEVEL)


def suite_test_summary(test: SuiteTest) -> str:
    """One line per test, for reports about reference code: `<id> failed: assert -1 == 5`."""
    return f"{test.test_id} {_outcome_text(test.outcome)}"


class _ProjectBuild:
    def __init__(self, environment: Environment, problem: Problem) -> None:
        self._environment = environment
        self._problem = problem

    def write(self, folder: str, trees: Mapping[str, ProjectTree], levels: int) -> Path:
        """`trees` by their directory in the problem, later ones over earlier ones; then the
        generated test files of levels 1 to `levels`. `folder` is synced to exactly those files:
        a file removed from a tree since the last build cannot linger in it, while unchanged files
        and the build tools' output stay, so the next build is incremental."""
        texts = self._texts(trees)
        if service_of(self._problem.meta) is None:
            texts.update(self._generated_tests(levels))
        workspace = self._environment.workspace
        workspace.sync_folder(folder, texts)
        return workspace.absolute(folder)

    def _generated_tests(self, levels: int) -> dict[str, str]:
        """A service project has none: its cases run over HTTP."""
        language = project_language(self._problem.meta)
        generator = self._environment.toolchains.project_test_generator(language)
        texts: dict[str, str] = {}
        for level in range(FIRST_LEVEL, levels + 1):
            tests = level_tests(self._problem, level)
            texts[tests.path] = generator.generate(tests)
        return texts

    def _texts(self, trees: Mapping[str, ProjectTree]) -> dict[str, str]:
        texts: dict[str, str] = {}
        unreadable: list[ContentIssue] = []
        directory = self._problem.meta.directory_name
        for source, tree in trees.items():
            for file in tree.files:
                if file.text is None:
                    location = f"{directory}/{source}/{file.path}"
                    unreadable.append(ContentIssue(location, "", NOT_TEXT))
                else:
                    texts[file.path] = file.text
        if unreadable:
            raise ContentError(unreadable)
        return texts


class _ProjectChecks:
    def __init__(
        self,
        environment: Environment,
        problem: Problem,
        language: Language,
        notify: ProgressNotice,
        selection: StressSelection,
    ) -> None:
        self._environment = environment
        self._problem = problem
        self._language = language
        self._notify = notify
        self._selection = selection
        self._release = release_of_content(problem.meta, language)
        self._stress: list[StressCheck] = []

    def verify(self) -> ProjectVerification:
        """The builds first: a case a generated test cannot express fails them both."""
        approach_id = self._problem.meta.approaches[0].id
        try:
            starter = starter_build(self._environment, self._problem)
            root = reference_build(self._environment, self._problem, approach_id)
        except ValueError as error:
            failed = ApproachResult(approach_id, (f"does not build: {error}",))
            result = LanguageResult(self._language, (failed,))
            return ProjectVerification(result, SuiteCheck(0, 0, (NOT_RUN,)))
        starter_problems = tuple(self._starter_problems(starter))
        plan = self._stress_plan(self._problem)
        graded = self._grade_reference(root, stress_plan=plan)
        approach = ApproachResult(approach_id, self._reference_failures(graded, approach_id))
        broken = tuple(self._broken(found) for found in self._brokens())
        result = LanguageResult(
            self._language, (approach,), starter_problems, broken, tuple(self._stress)
        )
        determinism = self._determinism(root) if graded.load_error is None else None
        return ProjectVerification(result, self._suite(root), determinism)

    def _stress_plan(self, problem: Problem) -> tuple[PlannedRun, ...]:
        return grading_stress_plan(problem, self._language, last_level(problem), self._selection)

    def _brokens(self) -> tuple[BrokenReference, ...]:
        """D7's broken overlays in the problem's one language."""
        languages = self._problem.meta.languages
        return tuple(
            found
            for found in project_brokens(self._problem)
            if found.covers(self._language, languages)
        )

    def _broken(self, broken: BrokenReference) -> ApproachResult:
        """D7: the broken overlay passes every sequential case and fails each `caught_by` stress
        case in at least `ceil(0.9 * N)` runs."""
        try:
            root = broken_build(self._environment, self._problem, broken.id)
        except ValueError as error:
            return ApproachResult(broken.id, (f"does not build: {error}",))
        caught_by = tuple(
            case
            for case in self._problem.cases
            if not isinstance(case.input, StressScenario) or case.id in broken.caught_by
        )
        plan = self._stress_plan(replace(self._problem, cases=caught_by))
        judgement = self._grade_reference(root, stress_plan=plan)
        if judgement.load_error is not None:
            return ApproachResult(
                broken.id, (f"does not load: {_error_text(judgement.load_error)}",)
            )
        failures = [f"sequential {failure}" for failure in self._failed_cases(judgement)]
        for verdict in judgement.stress:
            needed = required_failures(len(verdict.runs))
            check = StressCheck(broken.id, True, verdict, needed)
            self._stress.append(check)
            if not check.ok:
                failures.append(
                    f"{verdict.case_id} {verdict.variant} caught in {verdict.failed_runs}"
                    f"/{len(verdict.runs)} runs (needs {needed})"
                )
        return ApproachResult(broken.id, shown(failures))

    def _starter_problems(self, root: Path) -> Iterator[str]:
        """D1: the starter loads, and neither its cases nor its suite crash the runner."""
        grading = GradingRun(
            self._problem, self._language, root, FIRST_LEVEL, release=self._release
        )
        judgement = run_grading(self._environment, grading, self._notify)
        if judgement.load_error is not None:
            yield f"starter does not load: {_error_text(judgement.load_error)}"
        broken = (
            verdict.outcome
            for verdict in judgement.verdicts
            if isinstance(verdict.outcome, Crashed | TimedOut | NotRun)
        )
        outcome = next(broken, None)
        if outcome is not None:
            yield f"starter {outcome_summary(outcome)}"
        report = run_suite(self._environment, self._suite_run(root, FIRST_LEVEL), self._notify)
        yield from _suite_breakdowns(report)

    def _grade_reference(
        self, root: Path, clock_seed: int = 0, stress_plan: tuple[PlannedRun, ...] = ()
    ) -> Judgement:
        """The build at `root` at its last level: every case of every level, then `stress_plan`."""
        grading = GradingRun(
            self._problem,
            self._language,
            root,
            last_level(self._problem),
            release=self._release,
            clock_seed=clock_seed,
            stress_plan=stress_plan,
        )
        return run_grading(self._environment, grading, self._notify)

    def _reference_failures(self, judgement: Judgement, approach_id: str) -> tuple[str, ...]:
        """D3: every case of every level, each failure named with its level; D6: every run of
        every stress case passes."""
        if judgement.load_error is not None:
            return (f"does not load: {_error_text(judgement.load_error)}",)
        failures = self._failed_cases(judgement)
        for verdict in judgement.stress:
            check = StressCheck(approach_id, False, verdict, 0)
            self._stress.append(check)
            if not check.ok:
                failures.append(stress_failure(verdict))
        return shown(failures)

    def _determinism(self, root: Path) -> DeterminismVerdict | None:
        """D10: the reference graded `DETERMINISM_RUNS` more times, each run in a runner of its own,
        so that nothing one run left behind reaches the next, and each with a seed of its own, by
        which Python's loop orders the timers due at the same instant."""
        meta = self._problem.meta
        if meta.project is None or meta.project.clock is not ProjectClock.VIRTUAL:
            return None
        runs = [self._grade_reference(root, seed) for seed in range(DETERMINISM_RUNS)]
        config = self._environment.config
        guards = {
            verdict.case.id: resolve_hang_guard_ms(
                config, verdict.case.hang_guard_ms, meta.hang_guard_ms
            )
            for run in runs
            for verdict in run.verdicts
        }
        levels = {case.id: case.level for case in self._problem.cases}
        return judge_determinism(runs, guards, levels)

    def _failed_cases(self, judgement: Judgement) -> list[str]:
        levels = {case.id: case.level for case in self._problem.cases}
        return [
            f"level {levels.get(verdict.case.id)} {verdict_summary(verdict)}"
            for verdict in judgement.verdicts
            if verdict.status is not CaseStatus.PASS
        ]

    def _suite(self, root: Path) -> SuiteCheck:
        """D9: every test of the reference's suite passes or is skipped."""
        run = self._suite_run(root, last_level(self._problem))
        report = run_suite(self._environment, run, self._notify)
        passing = [test for test in report.tests if _passes(test.outcome)]
        failures: list[str] = []
        if report.load_error is not None:
            failures.append(f"does not run: {_error_text(report.load_error)}")
        failures += [suite_test_summary(test) for test in report.tests if not _passes(test.outcome)]
        if report.stopped_early is not None:
            failures.append(f"stopped early: {report.stopped_early}")
        return SuiteCheck(len(passing), len(report.tests), shown(failures))

    def _suite_run(self, root: Path, level: int) -> SuiteRun:
        return SuiteRun(self._problem.meta, self._language, root, level, release=self._release)


def _suite_breakdowns(report: SuiteReport) -> Iterator[str]:
    """D1: why the starter's suite did not run to its end: it could not start, a test hung or
    crashed the runner, or restarts ran out."""
    if report.load_error is not None:
        yield f"{STARTER_SUITE} does not run: {_error_text(report.load_error)}"
    broken = (test for test in report.tests if isinstance(test.outcome, Crashed | TimedOut))
    test = next(broken, None)
    if test is not None:
        yield f"{STARTER_SUITE}: {suite_test_summary(test)}"
    if report.stopped_early is not None:
        yield f"{STARTER_SUITE} stopped early: {report.stopped_early}"


def _passes(outcome: SuiteOutcome) -> bool:
    return isinstance(outcome, Passed | Skipped)


def _outcome_text(outcome: SuiteOutcome) -> str:
    match outcome:
        case Passed():
            return "ok"
        case AssertionFailed(message=message):
            return f"failed: {_first_line(message)}"
        case Raised(error=error):
            return f"error: {_error_text(error)}"
        case Skipped(message=message):
            return f"skipped: {message}"
        case TimedOut() | Crashed():
            return outcome_summary(outcome)


def _error_text(error: UserError) -> str:
    """The error's first line; a project that does not compile adds the compiler's first line,
    which its trace holds (docs/specs/runners.md#jvm-project-builds)."""
    text = f"{error.type}: {_first_line(error.message)}"
    if error.type == COMPILE_ERROR and error.trace:
        return f"{text}: {_first_line(error.trace)}"
    return text


def _first_line(text: str) -> str:
    return text.splitlines()[0] if text else text
