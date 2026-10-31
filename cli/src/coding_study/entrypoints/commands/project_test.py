"""`cstudy test` on a project problem (docs/specs/cli.md#project-problems).

Every test the suite reported is listed in run order with its status; a test of yours or of the
starter carries that tag. The run is feedback: a full pass points to `cstudy submit`, which grades
the project and opens its next level, or to `cstudy done` once a submission passed every level.
"""

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import timedelta

import typer
from rich.console import Console
from rich.text import Text

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.project_testing import (
    ProjectTestRequest,
    ProjectTestResult,
    run_project_tests,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.project_test_runs import SuiteOrigin, SuiteStatus, SuiteTestVerdict
from coding_study.domain.runs import Crashed, Raised, TimedOut, UserError
from coding_study.domain.suite_runs import AssertionFailed, Passed, Skipped, SuiteOutcome
from coding_study.domain.value_text import value_text
from coding_study.domain.workspace_projects import project_folder
from coding_study.entrypoints.commands.project_documents import project_test_document
from coding_study.entrypoints.commands.report_text import (
    EVERY_LEVEL_DONE,
    INDENT,
    clock_text,
    detail_line,
    error_text,
    labelled_lines,
    levels_text,
    status_line,
    trace_lines,
)
from coding_study.entrypoints.shared import ERROR_EXIT_CODES, ExitCode, print_error

FULL_PASS = "all passed. Next: cstudy submit"
SUBSET_PASSED = "all selected tests passed"
DEBUG_PASSED = "all passed (debug run: not recorded; cstudy test records the run)"
NO_TESTS = "no tests ran"
NOT_RUN = "NOT RUN"
BUILD_FAILED = "BUILD FAILED"
ORIGIN_GAP = "   "
_STYLES = {
    SuiteStatus.PASS: "green",
    SuiteStatus.FAIL: "bold red",
    SuiteStatus.ERROR: "bold red",
    SuiteStatus.SKIP: "dim",
    SuiteStatus.TIMEOUT: "yellow",
}
_FAILING_STYLE = "bold red"


def require_project_options(given: Sequence[str]) -> None:
    """`--perf`, `--stress`, `--seed`, `--time-limit` and `--debug-connect` have no meaning for a
    native suite."""
    if given:
        raise UsageError(f"{given[0]} is not available for project problems")


def project_test_exit_code(result: ProjectTestResult) -> int:
    """2 when code in the folder did not type-check, build or load, as for a single file; 0 when
    every test that ran passed and some test ran; 1 otherwise."""
    if result.code_failed_to_load:
        return ExitCode.USER_CODE_ERROR
    return ExitCode.SUCCESS if result.passed else ExitCode.FAILURES


@dataclass(frozen=True, slots=True)
class ProjectTestOptions:
    as_json: bool = False
    """`--json`: the run as one JSON document; notices go to standard error."""
    debug: bool = False
    """`--debug`: notices go to standard error too, where the ready line must be."""


class ProjectTestSession:
    def __init__(
        self,
        environment: Environment,
        request: ProjectTestRequest,
        output: Console,
        options: ProjectTestOptions,
    ) -> None:
        self._environment = environment
        self._request = request
        self._output = output
        self._options = options

    def run(self) -> int:
        result = run_project_tests(self._environment, self._request, self._notice)
        exit_code = project_test_exit_code(result)
        if self._options.as_json:
            typer.echo(json.dumps(project_test_document(result, exit_code), indent=2))
            return exit_code
        for line in ProjectTestReport(result).lines():
            self._output.print(line)
        return exit_code

    def watch(self) -> int:
        """Run now and after every change under the project folder, until interrupted."""
        environment, request = self._environment, self._request
        attempt = find_attempt(environment.progress, request.slug, request.language)
        watched = environment.workspace.absolute(project_folder(attempt.slug))
        exit_code = self._run_reporting_errors()
        for _ in environment.watcher.changes(watched):
            self._output.clear()
            exit_code = self._run_reporting_errors()
        return exit_code

    def _run_reporting_errors(self) -> int:
        try:
            return self.run()
        except tuple(ERROR_EXIT_CODES) as error:
            print_error(error)
            return ERROR_EXIT_CODES[type(error)]

    def _notice(self, line: str) -> None:
        if self._options.as_json or self._options.debug:
            typer.echo(line, err=True)
            return
        self._output.print(Text(line, style="dim"))


class ProjectTestReport:
    def __init__(self, result: ProjectTestResult) -> None:
        self._result = result

    def lines(self) -> Iterator[Text]:
        result = self._result
        yield Text(self._header(), style="bold")
        if result.debug is None and result.report is not None:
            yield Text(f"suite  {result.framework}, {result.suite_seconds:.1f}s")
        yield Text("")
        yield from self._body()
        yield Text("")
        yield Text(self._summary())
        if result.passed:
            yield Text(self._passed(), style="green")

    def _header(self) -> str:
        result = self._result
        parts = [result.meta.slug, result.language]
        if result.debug is not None:
            parts.append("debug")
        parts.append(levels_text(result.levels.ran_up_to, result.levels.progress.last))
        attempt = result.attempt
        if attempt.time_limit_s is not None:
            elapsed = attempt.solve_time(result.ran_at)
            limit = timedelta(seconds=attempt.time_limit_s)
            parts.append(f"timer {clock_text(elapsed)} / {clock_text(limit)}")
        return " · ".join(parts)

    def _body(self) -> Iterator[Text]:
        result = self._result
        if result.build_failure is not None:
            yield Text(BUILD_FAILED, style=_FAILING_STYLE)
            yield from (Text(line) for line in result.build_failure.diagnostics)
            return
        if result.load_error is not None:
            yield from _load_error(result.load_error)
            return
        for verdict in result.verdicts:
            yield from _test_lines(verdict)
        if result.stopped_early is not None:
            yield status_line(NOT_RUN, _FAILING_STYLE, result.stopped_early)

    def _summary(self) -> str:
        result = self._result
        tally = result.tally
        counted = f"{tally.passed}/{tally.total} passed" if result.ran else NO_TESTS
        if result.debug is not None:
            return counted
        return f"{counted} · total {result.duration_seconds:.1f}s"

    def _passed(self) -> str:
        result = self._result
        if result.debug is not None:
            return DEBUG_PASSED
        if not result.every_case:
            return SUBSET_PASSED
        return EVERY_LEVEL_DONE if result.every_level_done else FULL_PASS


def _test_lines(verdict: SuiteTestVerdict) -> Iterator[Text]:
    line = status_line(verdict.status.value, _STYLES[verdict.status], verdict.test.test_id)
    if verdict.origin is not SuiteOrigin.LEVEL:
        line.append(f"{ORIGIN_GAP}{verdict.origin}", style="dim")
    yield line
    outcome = verdict.test.outcome
    yield from _outcome_lines(outcome)
    stdout = outcome.stdout if isinstance(outcome, _WITH_STDOUT) else ""
    if stdout:
        lines = stdout.rstrip("\n").splitlines()
        yield from (detail_line(label, text) for label, text in labelled_lines("stdout", lines))


_WITH_STDOUT = (Passed, AssertionFailed, Raised, Skipped)


def _outcome_lines(outcome: SuiteOutcome) -> Iterator[Text]:
    match outcome:
        case AssertionFailed(message=message, comparison=comparison):
            yield from (Text(f"{INDENT}{line}") for line in message.splitlines())
            if comparison is not None:
                yield detail_line("expected", value_text(comparison.expected))
                yield detail_line("actual", value_text(comparison.actual))
        case Raised(error=error):
            yield detail_line("error", error_text(error))
            yield from (detail_line("", trace) for trace in trace_lines(error))
        case Skipped(message=message):
            yield detail_line("reason", message)
        case TimedOut(limit_ms=limit_ms):
            yield detail_line("limit", f"{limit_ms} ms hang guard")
        case Crashed(exit_code=exit_code, stderr_tail=stderr_tail):
            yield detail_line("crash", f"runner exited with code {exit_code}")
            yield from (detail_line("", line) for line in stderr_tail)
        case Passed():
            return


def _load_error(error: UserError) -> Iterator[Text]:
    yield status_line(SuiteStatus.ERROR.value, _FAILING_STYLE, f"load  {error_text(error)}")
    yield from (detail_line("", trace) for trace in trace_lines(error))
