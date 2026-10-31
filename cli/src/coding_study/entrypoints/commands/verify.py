"""`cstudy verify` (docs/specs/cli.md#cstudy-verify); the checks are in docs/specs/authoring.md."""

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.conformance_fixtures import load_conformance_suite
from coding_study.adapters.environment_factory import conformance_environment, load_environment
from coding_study.adapters.git_changed_files import GitChangedFiles
from coding_study.application.changed_problems import CHANGED_BASE, changed_problem_slugs
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    ProgressNotice,
)
from coding_study.application.reference_runs import LanguageResult
from coding_study.application.verify_conformance import (
    ConformanceRequest,
    FixtureVerification,
    verify_conformance,
)
from coding_study.application.verify_content import (
    ProblemVerification,
    VerifyReport,
    VerifyRequest,
    verify_content,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.generated_cases import DEFAULT_ORACLE_CASES
from coding_study.domain.problem import ContentStatus, Language, Track
from coding_study.domain.value_text import truncate
from coding_study.entrypoints.commands.list_problems import REFERENCE_LABELS
from coding_study.entrypoints.shared import ExitCode, add_command, command_environ, console

NAME = "verify"
NAME_WIDTH = 16
COLUMN_GAP = 2
DRAFT_GAP = " " * 6
DETAIL_INDENT = "  "
SEPARATOR = " · "
MAX_STRESS_RUNS = 100
NOT_LISTED = "-"
"""A fixture that lists none of the selected languages."""


def register(app: typer.Typer) -> None:
    add_command(app, verify, NAME)


def verify(
    context: typer.Context,
    slugs: Annotated[
        list[str] | None, typer.Argument(help="Problems to verify; default: all.")
    ] = None,
    changed: Annotated[
        bool, typer.Option("--changed", help="Only problems with files changed from main (git).")
    ] = False,
    track: Annotated[Track | None, typer.Option("--track", help="Only this track.")] = None,
    language: Annotated[Language | None, typer.Option("--lang", help="Only this language.")] = None,
    static: Annotated[
        bool, typer.Option("--static", help="Schema and static checks only; no execution.")
    ] = False,
    oracle: Annotated[
        bool, typer.Option("--oracle", help="Cross-check every approach against the oracle.")
    ] = False,
    oracle_cases: Annotated[
        int | None,
        typer.Option("--oracle-cases", metavar="N", min=1, help="Oracle inputs (default 200)."),
    ] = None,
    ladder: Annotated[
        bool,
        typer.Option("--ladder", help="Bench the references; check bands against time_class."),
    ] = False,
    conformance: Annotated[
        bool, typer.Option("--conformance", help="Run the runner conformance suite.")
    ] = False,
    require_ready: Annotated[
        bool, typer.Option("--require-ready", help="Fail any problem that is not ready.")
    ] = False,
    jobs: Annotated[
        int | None,
        typer.Option("--jobs", metavar="N", min=1, help="Parallel language runners."),
    ] = None,
    stress: Annotated[
        int | None,
        typer.Option(
            "--stress",
            metavar="N",
            min=1,
            max=MAX_STRESS_RUNS,
            help="Concurrent problems: runs per stress case and variant (default 10).",
        ),
    ] = None,
) -> None:
    """Content quality gate."""
    if oracle_cases is not None and not oracle:
        raise UsageError("--oracle-cases needs --oracle")
    if changed and (slugs or conformance):
        raise UsageError("--changed selects the problems itself; drop the slugs or --conformance")
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    output = console(context)
    selected = tuple(slugs or ())
    if changed:
        selected = changed_problem_slugs(
            environment.files, GitChangedFiles(environment.content_root)
        )
        if not selected:
            output.print(f"no problems changed relative to {CHANGED_BASE}")
            raise typer.Exit(ExitCode.SUCCESS)
    if conformance:
        request = ConformanceRequest(selected, language, jobs)
        raise typer.Exit(_conformance(environment, request, output))
    request = VerifyRequest(
        slugs=selected,
        track=track,
        language=language,
        static_only=static,
        oracle_cases=(oracle_cases or DEFAULT_ORACLE_CASES) if oracle else None,
        require_ready=require_ready,
        jobs=jobs,
        ladder=ladder,
        stress_runs=stress,
    )
    report = verify_content(environment, request, _notice(output))
    for line in _content_lines(report):
        output.print(line)
    raise typer.Exit(_content_exit_code(report))


def _notice(output: Console) -> ProgressNotice:
    def notify(line: str) -> None:
        output.print(Text(line, style="dim"))

    return notify


def _content_exit_code(report: VerifyReport) -> int:
    if not report.failed:
        return ExitCode.SUCCESS
    return ExitCode.CONTENT_ERROR if report.only_static_failures else ExitCode.FAILURES


def _content_lines(report: VerifyReport) -> Iterator[Text]:
    for problem in report.problems:
        yield from _ProblemLines(problem).lines()
    yield Text("")
    coverage = SEPARATOR.join(
        f"{entry.language} {entry.covered}/{entry.listed}" for entry in report.coverage
    )
    yield Text(f"coverage  {coverage}")
    yield _result_line(len(report.problems), report.failed)


def _result_line(total: int, failed: int) -> Text:
    style = "bold red" if failed else "green"
    return Text(f"result    {failed} failed{SEPARATOR}{total - failed} passed", style=style)


class _ProblemLines:
    def __init__(self, problem: ProblemVerification) -> None:
        self._problem = problem

    def lines(self) -> Iterator[Text]:
        problem = self._problem
        name = truncate(problem.directory.rpartition("/")[2], NAME_WIDTH)
        line = Text(name.ljust(NAME_WIDTH + COLUMN_GAP))
        if problem.static_errors:
            line.append(f"FAIL static: {problem.static_errors[0]}", style="bold red")
            yield line
            yield from _details(problem.static_errors[1:])
            yield from self._warnings()
            return
        line.append(SEPARATOR.join(self._parts()))
        draft = self._draft_note()
        if draft:
            line.append(f"{DRAFT_GAP}{draft}", style="dim")
        yield line
        yield from _details(self._failures())
        yield from self._warnings()

    def _parts(self) -> Iterator[str]:
        yield "static ok"
        for result in self._problem.languages:
            yield _language_part(result)
        suite = self._problem.suite
        if suite is not None:
            yield f"suite {suite.passing}/{suite.total}"
        oracle = self._problem.oracle
        if oracle is not None:
            yield f"oracle {oracle.agreed}/{oracle.total}"
        yield from _stress_parts(self._problem.languages)
        if self._problem.ladder:
            ladder_ok = all(result.passed for result in self._problem.ladder)
            yield f"ladder {'ok' if ladder_ok else 'FAIL'}"
        yield from (f"{check} n/a" for check in self._problem.skipped)
        if self._problem.dynamic_errors:
            yield "FAIL"
        if self._problem.ready_errors:
            yield "not ready"

    def _failures(self) -> Iterator[str]:
        problem = self._problem
        for result in problem.languages:
            yield from _language_failures(result)
        if problem.suite is not None:
            yield from (f"suite: {failure}" for failure in problem.suite.failures)
        if problem.oracle is not None:
            yield from (f"oracle: {failure}" for failure in problem.oracle.failures)
        for ladder in problem.ladder:
            label = REFERENCE_LABELS[ladder.language]
            yield from (f"ladder {label}: {issue}" for issue in ladder.problems)
            yield from (f"ladder {label}: {check.message}" for check in ladder.contradictions)
        yield from problem.dynamic_errors
        yield from (f"not ready: {reason}" for reason in problem.ready_errors)

    def _warnings(self) -> Iterator[Text]:
        ladder_notes = (
            f"ladder {REFERENCE_LABELS[ladder.language]}: {check.message}"
            for ladder in self._problem.ladder
            for check in (*ladder.tolerated, *ladder.unclassified)
        )
        for warning in (*self._problem.warnings, *ladder_notes):
            yield Text(f"{DETAIL_INDENT}warning: {warning}", style="yellow")

    def _draft_note(self) -> str | None:
        meta = self._problem.meta
        if meta is None or meta.status is not ContentStatus.DRAFT:
            return None
        covered = sum(1 for language in meta.languages if self._problem.covers(language))
        if covered == len(meta.languages):
            return None
        return f"draft (coverage {covered}/{len(meta.languages)})"


def _language_part(result: LanguageResult) -> str:
    label = REFERENCE_LABELS[result.language]
    total = len(result.approaches)
    if total == 0:
        return f"{label} FAIL" if result.problems else f"{label} -"
    status = "ok" if result.passed else "FAIL"
    return f"{label} {result.passing}/{total} {status}"


def _language_failures(result: LanguageResult) -> Iterator[str]:
    label = REFERENCE_LABELS[result.language]
    yield from (f"{label} {problem}" for problem in result.problems)
    for approach in result.approaches:
        yield from (f"{label} {approach.approach_id}: {failure}" for failure in approach.failures)
    for broken in result.broken:
        yield from (
            f"{label} broken {broken.approach_id}: {failure}" for failure in broken.failures
        )


def _stress_parts(results: Iterable[LanguageResult]) -> Iterator[str]:
    """D6 and D7: `stress 10/10 · slowest 8% · broken caught 11/11`."""
    checks = [check for result in results for check in result.stress]
    correct = [check for check in checks if not check.is_broken]
    if correct:
        worst = min(correct, key=lambda check: check.verdict.runs_passed)
        yield f"stress {worst.verdict.runs_passed}/{len(worst.verdict.runs)}"
        shares = [share for check in correct if (share := check.verdict.slowest_share) is not None]
        if shares:
            yield f"slowest {max(shares):.0%}"
    broken = [check for check in checks if check.is_broken]
    if broken:
        caught = sum(1 for check in broken if check.ok)
        yield f"broken caught {caught}/{len(broken)}"


def _details(messages: Iterable[str]) -> Iterator[Text]:
    return (Text(f"{DETAIL_INDENT}{message}") for message in messages)


def _conformance(environment: Environment, request: ConformanceRequest, output: Console) -> int:
    fixtures = conformance_environment(environment)
    suite = load_conformance_suite(environment.content_root)
    results = verify_conformance(fixtures, suite, request, _notice(output))
    width = max((len(result.directory.rpartition("/")[2]) for result in results), default=0)
    for result in results:
        for line in _fixture_lines(result, width + COLUMN_GAP):
            output.print(line)
    failed = sum(1 for result in results if not result.passed)
    output.print(Text(""))
    output.print(_result_line(len(results), failed))
    return ExitCode.FAILURES if failed else ExitCode.SUCCESS


def _fixture_lines(result: FixtureVerification, width: int) -> Iterator[Text]:
    line = Text(result.directory.rpartition("/")[2].ljust(width))
    parts = (
        f"{REFERENCE_LABELS[language.language]} {'ok' if language.passed else 'FAIL'}"
        for language in result.languages
    )
    if result.languages:
        line.append(SEPARATOR.join(parts))
    else:
        line.append("FAIL" if result.errors else NOT_LISTED)
    yield line
    yield from _details(result.errors)
    for language in result.languages:
        yield from _details(_language_failures(language))
