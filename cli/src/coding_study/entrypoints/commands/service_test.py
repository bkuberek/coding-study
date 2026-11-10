"""`cstudy test` on a service project (docs/specs/service-projects.md#how-you-reach-them).

It reports the two clocks apart: the startup, which no limit or result counts, and the run of
`commands.test` and the visible HTTP cases, from the moment the stack was ready. `--json` prints
the same as one document, with the progress on standard error, and `--events` streams it
(docs/specs/service-projects.md#what-you-see).
"""

import json
from collections.abc import Callable, Iterator

import typer
from rich.console import Console
from rich.text import Text

from coding_study.application.active_attempt import autograded_language
from coding_study.application.environment import Environment
from coding_study.application.project_runs import project_levels
from coding_study.application.run_events import CommandTested
from coding_study.application.service_events import stream_service_tests
from coding_study.application.service_grading import startup_load_error
from coding_study.application.service_lifecycle import (
    ServiceTestRequest,
    ServiceTestResult,
    run_service_tests,
)
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import CaseVerdict
from coding_study.domain.sandbox import StackStartError
from coding_study.entrypoints.commands._events import RunSummary, write_events
from coding_study.entrypoints.commands.project_documents import command_test_value
from coding_study.entrypoints.commands.report_text import (
    STATUS_STYLES,
    case_details,
    detail_line,
    status_line,
)
from coding_study.entrypoints.commands.run_document import (
    DECIMALS,
    case_value,
    error_value,
    levels_value,
    tally_value,
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


def run_service_test_json(environment: Environment, request: ServiceTestRequest) -> int:
    """`--json`: the document on standard output, the progress and the test's lines on standard
    error."""

    def to_stderr(line: str) -> None:
        typer.echo(line, err=True)

    result = run_service_tests(
        environment, ServiceTestRequest(request.slug, request.language, to_stderr), to_stderr
    )
    exit_code = _exit_code(result)
    typer.echo(json.dumps(service_test_document(result, exit_code), indent=2))
    return exit_code


def stream_service_test_command(environment: Environment, request: ServiceTestRequest) -> int:
    """`--events`."""
    return write_events(lambda emit: stream_service_tests(environment, request, emit), _summary)


def _summary(result: ServiceTestResult) -> RunSummary:
    exit_code = _exit_code(result)
    return RunSummary(exit_code, service_test_document(result, exit_code))


def service_test_document(result: ServiceTestResult, exit_code: int) -> dict[str, JsonValue]:
    """`tests` holds `commands.test`, empty when the stack did not become ready; `cases` the visible
    cases; `duration_s` the second clock and `startup_s` the first, which nothing counts."""
    attempt = result.attempt
    failure = result.failure
    levels = result.case_levels
    return {
        "slug": result.meta.slug,
        "language": autograded_language(attempt).value,
        "attempt_id": attempt.id,
        "outcome": _outcome(result),
        "exit_code": exit_code,
        "levels": levels_value(project_levels(result.meta, attempt.level_unlocked, None)),
        "load_error": None
        if failure is None
        else error_value(startup_load_error(failure, attempt.mode)),
        "tests": [] if result.outcome is None else [command_test_value(_tested(result))],
        "cases": [
            case_value(verdict) | {"level": levels.get(verdict.case.id)}
            for verdict in result.cases.verdicts
        ],
        "tally": tally_value(result.cases.tally()),
        "startup_s": round(result.startup_seconds, DECIMALS),
        "duration_s": round(result.test_seconds + result.cases_seconds, DECIMALS),
    }


def _tested(result: ServiceTestResult) -> CommandTested:
    assert result.outcome is not None
    return CommandTested(result.outcome, result.test_seconds, result.limit_s)


def _outcome(result: ServiceTestResult) -> str:
    if result.failure is not None:
        return "load_failed"
    return "passed" if result.passed else "failed"


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
