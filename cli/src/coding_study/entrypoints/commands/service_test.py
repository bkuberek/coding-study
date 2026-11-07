"""`cstudy test` on a service project (docs/specs/service-projects.md#how-you-reach-them).

It reports the two clocks apart: the startup, which no limit or result counts, and the run of
`commands.test` and the visible HTTP cases, from the moment the stack was ready.
"""

from collections.abc import Callable, Iterator

from rich.console import Console
from rich.text import Text

from coding_study.application.environment import Environment
from coding_study.application.service_lifecycle import (
    ServiceTestRequest,
    ServiceTestResult,
    run_service_tests,
)
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import CaseVerdict
from coding_study.domain.sandbox import StackStartError
from coding_study.entrypoints.commands.report_text import (
    STATUS_STYLES,
    case_details,
    detail_line,
    status_line,
)
from coding_study.entrypoints.shared import ExitCode

LABEL_WIDTH = 11
ID_WIDTH = 8
NOT_TAKEN = "cstudy test on a service project takes none of"


def require_service_options(given: tuple[str, ...]) -> None:
    """The flags of a native run do not apply: debug through your own IDE against `cstudy dev`."""
    if given:
        raise UsageError(f"{NOT_TAKEN} {', '.join(given)}")


def run_service_test_command(
    environment: Environment, request: ServiceTestRequest, output: Console
) -> int:
    """Runs the tests with their output as it comes; the exit code `cstudy test` ends with."""
    result = run_service_tests(
        environment,
        ServiceTestRequest(request.slug, request.language, _printer(output)),
        lambda line: output.print(Text(line, style="dim")),
    )
    for line in _report(result):
        output.print(line)
    return _exit_code(result)


def _printer(output: Console) -> Callable[[str], None]:
    def printed(line: str) -> None:
        output.print(Text(line))

    return printed


def _exit_code(result: ServiceTestResult) -> int:
    if result.failure is not None:
        return ExitCode.USER_CODE_ERROR
    return ExitCode.SUCCESS if result.passed else ExitCode.FAILURES


def _report(result: ServiceTestResult) -> Iterator[Text]:
    if result.failure is not None:
        yield from _failure(result.failure)
        return
    outcome = result.outcome
    assert outcome is not None
    yield from _cases(result)
    yield _line("startup", f"{result.startup_seconds:.1f} s, not counted")
    yield _line("test", _test_text(result))
    yield _line("cases", _cases_text(result))
    yield _line("total", f"{result.total_seconds:.1f} s")


def _test_text(result: ServiceTestResult) -> str:
    outcome = result.outcome
    assert outcome is not None
    if outcome.timed_out:
        return f"commands.test did not finish within {result.limit_s} s"
    verdict = "passed" if result.command_passed else f"failed, exit {outcome.exit_code}"
    return f"commands.test {verdict} in {result.test_seconds:.1f} s"


def _cases_text(result: ServiceTestResult) -> str:
    cases = result.cases
    return (
        f"{cases.count(CaseStatus.PASS)}/{cases.case_count} visible passed "
        f"in {result.cases_seconds:.1f} s"
    )


def _cases(result: ServiceTestResult) -> Iterator[Text]:
    for verdict in result.cases.verdicts:
        yield from _verdict(verdict)


def _verdict(verdict: CaseVerdict) -> Iterator[Text]:
    style = STATUS_STYLES[verdict.status]
    yield status_line(verdict.status.value, style, verdict.case.id.ljust(ID_WIDTH))
    if verdict.status is not CaseStatus.PASS:
        for name, value in case_details(verdict, None):
            yield detail_line(name, value)


def _failure(failure: StackStartError) -> Iterator[Text]:
    yield Text(str(failure), style="bold red")
    for line in failure.output.splitlines():
        yield Text(line, style="dim")


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
