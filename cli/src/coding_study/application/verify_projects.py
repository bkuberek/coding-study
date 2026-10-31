"""`cstudy verify` on a project problem: D1, D3 and D9 (docs/specs/authoring.md#dynamic).

D1: the starter, copied with level 1's generated tests as `cstudy start` seeds a folder, loads: a
grading job of level 1 reports every case without a load error (the cases may fail), and its
native suite runs to its end without crashing the runner. D3: the reference, the starter with its
overlay and the generated tests of every level (docs/specs/runners.md#reference-materialization),
passes every case of every level. D9: the reference passes its native suite. Every job gets a
runner of its own (docs/specs/runners.md#project-jobs).
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from coding_study.application.environment import Environment
from coding_study.application.ports import ProgressNotice
from coding_study.application.project_runs import GradingRun, SuiteRun, run_grading, run_suite
from coding_study.application.reference_runs import ApproachResult, LanguageResult, shown
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.judging import Judgement, outcome_summary, verdict_summary
from coding_study.domain.layout import BUILD_DIRECTORY
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Language, Problem
from coding_study.domain.problem_files import SOLUTIONS_DIRECTORY, STARTER_DIRECTORY
from coding_study.domain.project import (
    NO_PROJECT_FILES,
    PATH_SEPARATOR,
    ProjectTree,
    project_language,
)
from coding_study.domain.project_tests import level_tests
from coding_study.domain.runs import Crashed, NotRun, Raised, TimedOut, UserError
from coding_study.domain.stub_check import STUB_DIRECTORY
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Passed,
    Skipped,
    SuiteOutcome,
    SuiteReport,
    SuiteTest,
)

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


def verify_project(
    environment: Environment, problem: Problem, language: Language, notify: ProgressNotice
) -> ProjectVerification:
    """D1, D3 and D9 in `language`, the problem's one language.

    Raises LanguageNotSetUpError without a test generator for the language, RunnerStartError
    when its runner cannot run project jobs, and ContentError for a project file that is not text.
    """
    return _ProjectChecks(environment, problem, language, notify).verify()


def reference_build(environment: Environment, problem: Problem, approach_id: str) -> Path:
    """The approach's build: the starter, its overlay over it, then the generated test file of
    every level; returns the absolute root.

    Files are written over the previous build, so a file removed from the starter or the overlay
    stays until `.cs/build/projects/` is deleted.
    """
    files = problem.project_files or NO_PROJECT_FILES
    trees = {
        STARTER_DIRECTORY: files.starter or _NO_FILES,
        f"{SOLUTIONS_DIRECTORY}/{approach_id}": files.overlays.get(approach_id, _NO_FILES),
    }
    folder = f"{PROJECT_BUILDS}/{problem.meta.slug}/{approach_id}"
    return _ProjectBuild(environment, problem).write(folder, trees, last_level(problem))


def starter_build(environment: Environment, problem: Problem) -> Path:
    """The starter with level 1's generated test file, as `cstudy start` seeds a project folder;
    returns the absolute root."""
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
        generated test files of levels 1 to `levels`."""
        texts = self._texts(trees)
        workspace = self._environment.workspace
        for path, text in texts.items():
            workspace.write_text(f"{folder}{PATH_SEPARATOR}{path}", text)
        language = project_language(self._problem.meta)
        generator = self._environment.toolchains.project_test_generator(language)
        for level in range(FIRST_LEVEL, levels + 1):
            tests = level_tests(self._problem, level)
            workspace.write_text(f"{folder}{PATH_SEPARATOR}{tests.path}", generator.generate(tests))
        return workspace.absolute(folder)

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
    ) -> None:
        self._environment = environment
        self._problem = problem
        self._language = language
        self._notify = notify

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
        approach = ApproachResult(approach_id, self._reference_failures(root))
        result = LanguageResult(self._language, (approach,), starter_problems)
        return ProjectVerification(result, self._suite(root))

    def _starter_problems(self, root: Path) -> Iterator[str]:
        """D1: the starter loads, and neither its cases nor its suite crash the runner."""
        grading = GradingRun(self._problem, self._language, root, FIRST_LEVEL)
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

    def _reference_failures(self, root: Path) -> tuple[str, ...]:
        """D3: every case of every level, each failure named with its level."""
        grading = GradingRun(self._problem, self._language, root, last_level(self._problem))
        judgement = run_grading(self._environment, grading, self._notify)
        if judgement.load_error is not None:
            return (f"does not load: {_error_text(judgement.load_error)}",)
        return shown(self._failed_cases(judgement))

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
        return SuiteRun(self._problem.meta, self._language, root, level)


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
    return f"{error.type}: {_first_line(error.message)}"


def _first_line(text: str) -> str:
    return text.splitlines()[0] if text else text
