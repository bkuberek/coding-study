"""The lines `cstudy test` and `cstudy submit` print for a case or a test
(docs/specs/cli.md#cstudy-test): a status column, then details under it, one label each."""

from collections.abc import Iterator
from datetime import timedelta

from rich.text import Text

from coding_study.domain.cases import FunctionInput
from coding_study.domain.judging import CaseStatus, CaseVerdict, RunnableCase, outcome_summary
from coding_study.domain.runs import (
    Crashed,
    InvalidOutput,
    NotRun,
    Raised,
    Returned,
    RunInput,
    Stalled,
    StressCompleted,
    TimedOut,
    UserError,
)
from coding_study.domain.time_limits import NANOSECONDS_PER_MILLISECOND
from coding_study.domain.value_text import value_text
from coding_study.entrypoints.commands.run_document import operations_up_to

STATUS_WIDTH = 9
LABEL_WIDTH = 10
INDENT = " " * STATUS_WIDTH
SECONDS_PER_MINUTE = 60
MILLISECONDS_PER_SECOND = 1000
STATUS_STYLES = {
    CaseStatus.PASS: "green",
    CaseStatus.FAIL: "bold red",
    CaseStatus.ERROR: "bold red",
    CaseStatus.INVALID: "bold red",
    CaseStatus.TIMEOUT: "yellow",
    CaseStatus.TLE: "yellow",
    CaseStatus.STALLED: "bold red",
    CaseStatus.NOT_RUN: "dim",
}


def case_details(verdict: CaseVerdict, comparator_label: str | None) -> Iterator[tuple[str, str]]:
    outcome = verdict.outcome
    case = verdict.case
    match outcome:
        case Returned(output=output):
            yield ("input", input_text(case.input))
            yield ("expected", expected_text(case, comparator_label))
            yield ("actual", value_text(output))
            if verdict.mismatch is not None and verdict.mismatch.detail:
                yield ("reason", verdict.mismatch.detail)
        case Raised(error=error, op_index=op_index, partial_output=partial):
            yield ("input", input_text(operations_up_to(case.input, op_index)))
            yield ("error", error_text(error))
            yield from (("", trace) for trace in trace_lines(error))
            if op_index is not None:
                yield ("outputs", value_text(list(partial)))
        case InvalidOutput(reason=reason):
            yield ("input", input_text(case.input))
            yield ("reason", reason)
        case TimedOut(limit_ms=limit_ms):
            yield ("input", input_text(case.input))
            yield ("limit", f"{limit_ms} ms hang guard")
        case Crashed(exit_code=exit_code, stderr_tail=stderr_tail):
            yield ("input", input_text(case.input))
            yield ("crash", f"runner exited with code {exit_code}")
            yield from (("", line) for line in stderr_tail)
        case NotRun(reason=reason):
            yield ("reason", reason)
        case StressCompleted() | Stalled():
            yield ("reason", outcome_summary(outcome))
    if case.note:
        yield ("note", case.note)
    if isinstance(outcome, Returned | Raised | InvalidOutput) and outcome.stdout:
        yield from labelled_lines("stdout", outcome.stdout.rstrip("\n").splitlines())


def labelled_lines(label: str, lines: list[str]) -> Iterator[tuple[str, str]]:
    for index, line in enumerate(lines):
        yield (label if index == 0 else "", line)


def expected_text(case: RunnableCase, comparator_label: str | None) -> str:
    expected = case.expected
    text = value_text(expected.value) if expected is not None else "any valid answer"
    return f"{text}  ({comparator_label})" if comparator_label else text


def input_text(run_input: RunInput) -> str:
    if isinstance(run_input, FunctionInput):
        return "  ".join(
            f"{name}={value_text(value)}" for name, value in run_input.arguments.items()
        )
    args = value_text([list(arguments) for arguments in run_input.args])
    return f"ops={value_text(list(run_input.ops))}  args={args}"


def error_text(error: UserError) -> str:
    return f"{error.type}: {error.message}" if error.message else error.type


def trace_lines(error: UserError) -> list[str]:
    return error.trace.splitlines() if error.trace else []


def detail_line(label: str, value: str) -> Text:
    line = Text(INDENT)
    line.append(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line


def duration_text(nanoseconds: int) -> str:
    milliseconds = nanoseconds / NANOSECONDS_PER_MILLISECOND
    if milliseconds < 10:
        return f"{milliseconds:.2f}ms"
    if milliseconds < 100:
        return f"{milliseconds:.1f}ms"
    if milliseconds < MILLISECONDS_PER_SECOND:
        return f"{milliseconds:.0f}ms"
    return f"{milliseconds / MILLISECONDS_PER_SECOND:.2f}s"


def levels_text(ran_up_to: int, last: int) -> str:
    covered = f"level {ran_up_to}" if ran_up_to == 1 else f"levels 1-{ran_up_to}"
    return f"{covered} of {last}"


def clock_text(duration: timedelta) -> str:
    minutes, seconds = divmod(int(duration.total_seconds()), SECONDS_PER_MINUTE)
    return f"{minutes:02d}:{seconds:02d}"


def status_line(status: str, style: str, rest: str) -> Text:
    """`status` in its column and style, then `rest`."""
    line = Text(status.ljust(STATUS_WIDTH), style=style)
    line.append(rest)
    return line
