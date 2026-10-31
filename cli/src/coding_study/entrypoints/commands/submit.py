"""`cstudy submit` (docs/specs/cli.md#cstudy-submit).

One line per graded level with its passed count, then the visible cases with their status and the
failing hidden ones with their input, expected and actual; a mock attempt names no hidden case and
only counts the failing ones per level. A submission that opens a level names the methods it adds,
its test file and the rewritten statement.
"""

import json
from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.application.submit_project import (
    OpenedLevel,
    SubmitRequest,
    SubmitResult,
    submit_project,
)
from coding_study.domain.cases import OperationSequence
from coding_study.domain.judging import CaseStatus, CaseVerdict
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.project import in_language_operations
from coding_study.domain.submissions import LevelTally
from coding_study.entrypoints.commands.project_documents import submit_document
from coding_study.entrypoints.commands.report_text import (
    STATUS_STYLES,
    case_details,
    clock_text,
    detail_line,
    error_text,
    levels_text,
    status_line,
    trace_lines,
)
from coding_study.entrypoints.shared import (
    OPTIONAL_TARGET_HELP,
    ExitCode,
    add_command,
    command_environ,
    console,
)

NAME = "submit"
LABEL_WIDTH = 11
LEVEL_WIDTH = 9
MIN_ID_WIDTH = 6
DONE_HINT = "all passed · every level done. Next: cstudy done --rating easy|ok|hard"
DID_NOT_LOAD = "the code did not load"
HIDDEN = "hidden"


def register(app: typer.Typer) -> None:
    add_command(app, submit, NAME)


def submit(
    context: typer.Context,
    slug: Annotated[str | None, typer.Argument(help=OPTIONAL_TARGET_HELP)] = None,
    level: Annotated[
        int | None,
        typer.Option("--level", metavar="N", min=1, help="Grade levels 1 to N (unlocked only)."),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the report.")
    ] = False,
) -> None:
    """Grade a project problem and open its next level."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug), Path.cwd())
    output = console(context)

    def notice(line: str) -> None:
        if as_json:
            typer.echo(line, err=True)
        else:
            output.print(Text(line, style="dim"))

    request = SubmitRequest(target.slug, target.language, level)
    result = submit_project(environment, request, notice)
    exit_code = submit_exit_code(result)
    if as_json:
        typer.echo(json.dumps(submit_document(result, exit_code), indent=2))
    else:
        for line in SubmitReport(result).lines():
            output.print(line)
    raise typer.Exit(exit_code)


def submit_exit_code(result: SubmitResult) -> int:
    """0 when every graded case passed, 1 when one did not, 2 when the code did not load."""
    judgement = result.judgement
    if judgement.load_error is not None:
        return ExitCode.USER_CODE_ERROR
    return ExitCode.SUCCESS if judgement.passed else ExitCode.FAILURES


class SubmitReport:
    def __init__(self, result: SubmitResult) -> None:
        self._result = result
        self._levels = {case.id: case.level for case in result.cases}
        longest = max((len(case.id) for case in result.cases), default=0)
        self._id_width = max(MIN_ID_WIDTH, longest + 2)

    def lines(self) -> Iterator[Text]:
        yield Text(self._header(), style="bold")
        yield Text("")
        yield from (self._level_line(tally) for tally in self._result.level_tallies)
        yield from self._cases()
        yield Text("")
        yield Text(self._summary())
        yield from self._after()

    def _header(self) -> str:
        result = self._result
        last = result.levels.progress.last
        parts = [
            result.meta.slug,
            result.language,
            f"submit {levels_text(result.levels.ran_up_to, last)}",
        ]
        attempt = result.attempt
        if attempt.time_limit_s is not None:
            elapsed = attempt.solve_time(result.submitted_at)
            limit = timedelta(seconds=attempt.time_limit_s)
            parts.append(f"timer {clock_text(elapsed)} / {clock_text(limit)}")
        return " · ".join(parts)

    def _level_line(self, tally: LevelTally) -> Text:
        status = CaseStatus.PASS if tally.all_passed else CaseStatus.FAIL
        counts = f"{tally.passed}/{tally.total} ({tally.visible_total} visible, "
        counts += f"{tally.hidden_total} hidden)"
        if self._result.is_mock and tally.hidden_failed:
            noun = "case" if tally.hidden_failed == 1 else "cases"
            counts += f" · {tally.hidden_failed} hidden {noun} failed"
        line = Text(f"level {tally.level}".ljust(LEVEL_WIDTH))
        line.append_text(status_line(status.value, STATUS_STYLES[status], counts))
        return line

    def _cases(self) -> Iterator[Text]:
        judgement = self._result.judgement
        if judgement.load_error is not None:
            error = judgement.load_error
            failing = STATUS_STYLES[CaseStatus.ERROR]
            yield status_line(CaseStatus.ERROR.value, failing, f"load  {error_text(error)}")
            yield from (detail_line("", trace) for trace in trace_lines(error))
            return
        for verdict in judgement.verdicts:
            if self._shown(verdict):
                yield from self._verdict(verdict)

    def _shown(self, verdict: CaseVerdict) -> bool:
        """Visible cases always; failing hidden ones only in practice."""
        if verdict.case.visible:
            return True
        return verdict.status is not CaseStatus.PASS and not self._result.is_mock

    def _verdict(self, verdict: CaseVerdict) -> Iterator[Text]:
        case = verdict.case
        level = f"level {self._levels.get(case.id, FIRST_LEVEL)}"
        label = level if case.visible else f"{HIDDEN} · {level}"
        line = status_line(
            verdict.status.value, STATUS_STYLES[verdict.status], case.id.ljust(self._id_width)
        )
        line.append(label, style="dim")
        yield line
        if verdict.status is CaseStatus.PASS:
            return
        named = self._in_language(verdict)
        details = case_details(named, self._result.comparator.label)
        yield from (detail_line(name, value) for name, value in details)

    def _in_language(self, verdict: CaseVerdict) -> CaseVerdict:
        """The operations as the project's language names its methods."""
        case = verdict.case
        if not isinstance(case.input, OperationSequence):
            return verdict
        named = in_language_operations(case.input, self._result.language)
        return replace(verdict, case=replace(case, input=named))

    def _summary(self) -> str:
        result = self._result
        tally = result.submission.tally
        counted = f"{tally.passed}/{tally.total} passed"
        levels = result.levels
        if result.judgement.load_error is not None:
            return f"{counted} · {DID_NOT_LOAD}"
        if not result.every_level:
            covered = _levels_phrase(levels.ran_up_to)
            return f"{counted} · {covered} only: opens no level and does not count for cstudy done"
        if result.opened is not None:
            opened = result.opened
            return f"{counted} · level {opened.level} unlocked: {opened.title}"
        if result.judgement.passed:
            return counted
        if levels.progress.all_unlocked:
            return f"{counted} · every level is done when {_passes(levels.ran_up_to)}"
        return f"{counted} · level {levels.unlocked + 1} opens when {_passes(levels.ran_up_to)}"

    def _after(self) -> Iterator[Text]:
        result = self._result
        if result.opened is not None:
            yield from _opened_lines(result.opened)
        elif result.finished_every_level:
            yield Text(DONE_HINT, style="green")


def _opened_lines(opened: OpenedLevel) -> Iterator[Text]:
    if opened.methods:
        yield _line("add", ", ".join(opened.methods))
    tests = opened.tests
    count = f"{tests.tests} {'test' if tests.tests == 1 else 'tests'}"
    yield _line("tests", f"{tests.path} ({count})")
    yield _line("statement", f"{opened.statement} (updated)")


def _levels_phrase(up_to: int) -> str:
    return "level 1" if up_to == FIRST_LEVEL else f"levels 1-{up_to}"


def _passes(up_to: int) -> str:
    """`level 1 passes`, or `levels 1-2 pass`."""
    verb = "passes" if up_to == FIRST_LEVEL else "pass"
    return f"{_levels_phrase(up_to)} {verb}"


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
