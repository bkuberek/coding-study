"""A suite job run by pytest inside the runner (docs/specs/runners.md#suite-job).

pytest runs on the case thread like every job, with its own capture off: a plugin of the runner's
writes `case_start` before each test's setup and `case_result` after its teardown, and captures
what the test prints in between, so the CLI's hang guard and crash handling see the test in
progress. pytest's own report goes to a buffer, kept only to explain a run pytest refused.

Tests are left out by exact node id (`skip`); pytest's `--deselect` matches node id prefixes and
would also leave out `test_x2` with `test_x`. A test file that fails to import is one `error`
whose id is the file, and the other files still run.
"""

import os
import time
from collections.abc import Generator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from cs_runner.capture import capture_output
from cs_runner.events import AssertionFailed, EventWriter, Passed, Raised, Skipped, SuiteOutcome
from cs_runner.failures import UserError, UserFolder, describe
from cs_runner.loading import add_project_root
from cs_runner.request import SuiteJob

PLUGIN_AUTOLOAD_VARIABLE = "PYTEST_DISABLE_PLUGIN_AUTOLOAD"
ID_SEPARATOR = "::"
PATH_SEPARATOR = "/"
CALL_PHASE = "call"
SKIP_REASON_PREFIX = "Skipped: "
EXPECTED_FAILURE = "xfail"
REFUSED_RUNS: Mapping[int, str] = {
    pytest.ExitCode.USAGE_ERROR: "UsageError",
    pytest.ExitCode.INTERNAL_ERROR: "InternalError",
}
"""pytest's exit codes for a run it could not start, with the `load_error` type of each."""
FAILURE_TYPES = (AssertionError, pytest.fail.Exception)
"""Exceptions that make a test `failed`; any other makes it an `error`."""

type Report = pytest.TestReport | pytest.CollectReport


def run_pytest(job: SuiteJob, events: EventWriter) -> None:
    """Every test of the project, through `job_start` to `job_end` (written by the caller)."""
    add_project_root(job.root)
    os.environ[PLUGIN_AUTOLOAD_VARIABLE] = "1"
    reporter = _Reporter(job, events)
    with capture_output() as pytest_output:
        exit_code = pytest.main(_arguments(job), plugins=[reporter])
    refused = REFUSED_RUNS.get(exit_code)
    if refused is not None and not reporter.reported_any:
        events.load_error(job.job_id, UserError(refused, pytest_output.text().strip()))


def _arguments(job: SuiteJob) -> list[str]:
    """Discovery is pytest's own from the root, the working directory, under the project's
    settings; these only add the runner's needs."""
    ignored = [f"--ignore={Path(job.root, path)}" for path in job.exclude]
    return [
        "--rootdir",
        job.root,
        "-p",
        "no:cacheprovider",
        "--capture=no",
        "--continue-on-collection-errors",
        *ignored,
    ]


@dataclass(frozen=True, slots=True)
class _Selection:
    select: tuple[str, ...]
    skip: frozenset[str]

    def runs(self, test_id: str) -> bool:
        if test_id in self.skip:
            return False
        return not self.select or any(_names(test_id, wanted) for wanted in self.select)

    def reports(self, collector_id: str) -> bool:
        """A collector that failed is reported unless it was before a restart, or `select`
        names only tests outside it."""
        if not collector_id or collector_id in self.skip:
            return False
        return not self.select or any(_within(wanted, collector_id) for wanted in self.select)


def _names(test_id: str, wanted: str) -> bool:
    """`wanted` is the whole node id or its last part (`test_ex1`)."""
    return test_id == wanted or test_id.endswith(f"{ID_SEPARATOR}{wanted}")


def _within(wanted: str, collector_id: str) -> bool:
    """A last part alone (`test_ex1`) could be in any file."""
    if ID_SEPARATOR not in wanted:
        return True
    return wanted == collector_id or wanted.startswith(
        (f"{collector_id}{ID_SEPARATOR}", f"{collector_id}{PATH_SEPARATOR}")
    )


@dataclass(slots=True)
class _TestRun:
    """What pytest reported for one test, or one collector, so far."""

    reports: list[Report] = field(default_factory=list[Report])
    exceptions: dict[str, BaseException] = field(default_factory=dict[str, BaseException])
    """The exception of each failed phase (`setup`, `call`, `teardown` or `collect`)."""


class _Reporter:
    """The pytest plugin that turns pytest's hooks into the job's events."""

    def __init__(self, job: SuiteJob, events: EventWriter) -> None:
        self._job = job
        self._events = events
        self._selection = _Selection(job.select, frozenset(job.skip))
        self._code = UserFolder(job.root)
        self._runs: dict[str, _TestRun] = {}
        self.reported_any = False

    def pytest_collection_modifyitems(
        self, config: pytest.Config, items: list[pytest.Item]
    ) -> None:
        dropped = [item for item in items if not self._selection.runs(item.nodeid)]
        if dropped:
            items[:] = [item for item in items if self._selection.runs(item.nodeid)]
            config.hook.pytest_deselected(items=dropped)

    def pytest_exception_interact(
        self, node: pytest.Item | pytest.Collector, call: pytest.CallInfo[object], report: Report
    ) -> None:
        if call.excinfo is not None:
            self._run(report.nodeid).exceptions[report.when or ""] = call.excinfo.value

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.passed or not self._selection.reports(report.nodeid):
            return
        run = self._run(report.nodeid)
        run.reports.append(report)
        self._events.case_start(self._job.job_id, report.nodeid)
        self._result(report.nodeid, self._outcome(run, 0, ""))

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        self._run(report.nodeid).reports.append(report)

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(
        self, item: pytest.Item, nextitem: pytest.Item | None
    ) -> Generator[None, object, object]:
        """One test, from its setup to its teardown, with what it prints captured."""
        test_id = item.nodeid
        self._events.case_start(self._job.job_id, test_id)
        started_ns = time.perf_counter_ns()
        try:
            with capture_output() as output:
                result = yield
        except BaseException as interruption:
            duration_ns = time.perf_counter_ns() - started_ns
            self._result(test_id, Raised(describe(interruption, self._code), duration_ns))
            raise
        duration_ns = time.perf_counter_ns() - started_ns
        self._result(test_id, self._outcome(self._run(test_id), duration_ns, output.text()))
        return result

    def _run(self, node_id: str) -> _TestRun:
        return self._runs.setdefault(node_id, _TestRun())

    def _result(self, node_id: str, outcome: SuiteOutcome) -> None:
        self._events.case_result(self._job.job_id, node_id, outcome)
        self._runs.pop(node_id, None)
        self.reported_any = True

    def _outcome(self, run: _TestRun, duration_ns: int, stdout: str) -> SuiteOutcome:
        """The first phase that did not pass decides: a failure, or a skip."""
        for report in run.reports:
            if report.failed:
                exception = run.exceptions.get(report.when or "")
                return self._failure(report, exception, duration_ns, stdout)
            if report.skipped:
                return Skipped(_skip_reason(report), duration_ns, stdout)
        return Passed(duration_ns, stdout)

    def _failure(
        self, report: Report, exception: BaseException | None, duration_ns: int, stdout: str
    ) -> SuiteOutcome:
        """A failed assertion in the test itself is `failed` (a strict xfail that passed has no
        exception); anything else, in a fixture or at import, is an `error`."""
        if exception is None and report.when == CALL_PHASE:
            return AssertionFailed(str(report.longrepr), duration_ns, stdout)
        if isinstance(exception, FAILURE_TYPES) and report.when == CALL_PHASE:
            return AssertionFailed(str(exception), duration_ns, stdout)
        if exception is None:
            return Raised(UserError("Error", str(report.longrepr)), duration_ns, stdout)
        return Raised(describe(_original(exception), self._code), duration_ns, stdout)


def _original(exception: BaseException) -> BaseException:
    """pytest reports a test file that does not import as a `CollectError` raised from the
    import's own exception."""
    if isinstance(exception, pytest.Collector.CollectError) and exception.__cause__ is not None:
        return exception.__cause__
    return exception


def _skip_reason(report: Report) -> str:
    expected_failure = getattr(report, "wasxfail", None)
    if isinstance(expected_failure, str):
        return f"{EXPECTED_FAILURE}: {expected_failure}" if expected_failure else EXPECTED_FAILURE
    longrepr = report.longrepr
    if isinstance(longrepr, tuple):
        return longrepr[2].removeprefix(SKIP_REASON_PREFIX)
    return str(longrepr)
