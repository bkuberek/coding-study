"""`cstudy bench` (docs/specs/cli.md#cstudy-bench, docs/specs/performance-analysis.md).

Prints the ladder table (every reference and the user per size, slope, band, memory band), then
the verdict, space and history lines. Every verdict line names its confidence; no percentile is
ever printed.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.application.run_bench import (
    BenchOptions,
    BenchResult,
    RunBenchRequest,
    run_bench,
)
from coding_study.domain.bench_stats import (
    SizeStatus,
    TargetAnalysis,
    duration_text,
    size_text,
)
from coding_study.domain.bench_verdict import GrowthVerdict, History, SpaceVerdict
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.entrypoints.shared import (
    OPTIONAL_TARGET_HELP,
    ExitCode,
    add_command,
    command_environ,
    console,
)

NAME = "bench"
USER_LABEL = "you"
LABEL = "{:<10}"
PERCENT = 100
_CELLS = {
    SizeStatus.BUDGET_EXCEEDED: "budget",
    SizeStatus.FAILED: "error",
    SizeStatus.NOT_RUN: "-",
}


def register(app: typer.Typer) -> None:
    add_command(app, bench, NAME)


def bench(
    context: typer.Context,
    slug: Annotated[
        str | None,
        typer.Argument(help=OPTIONAL_TARGET_HELP),
    ] = None,
    language: Annotated[
        Language | None, typer.Option("--lang", help="Language; default: the attempt's.")
    ] = None,
    sizes: Annotated[
        str | None,
        typer.Option("--sizes", metavar="LIST", help="Comma-separated sizes, e.g. 100,1000."),
    ] = None,
    reps: Annotated[
        int | None, typer.Option("--reps", metavar="N", min=1, help="Timed repetitions per size.")
    ] = None,
    refs_only: Annotated[
        bool, typer.Option("--refs-only", help="Bench the references only.")
    ] = False,
    no_memory: Annotated[
        bool, typer.Option("--no-memory", help="Skip the memory measurements.")
    ] = False,
) -> None:
    """Complexity ladder and memory analysis."""
    options = BenchOptions(parse_sizes(sizes), reps, False if no_memory else None)
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug, language), Path.cwd())
    request = RunBenchRequest(target.slug, target.language, options, refs_only)
    output = console(context)
    result = run_bench(environment, request, lambda line: output.print(Text(line, style="dim")))
    for line in BenchReportLines(result).lines():
        output.print(line)
    raise typer.Exit(bench_exit_code(result))


def parse_sizes(text: str | None) -> tuple[int, ...]:
    if text is None:
        return ()
    try:
        sizes = tuple(int(part) for part in text.split(",") if part.strip())
    except ValueError:
        raise UsageError(f"--sizes takes comma-separated whole numbers, got {text!r}") from None
    if not sizes or any(size < 1 for size in sizes):
        raise UsageError(f"--sizes takes positive sizes, got {text!r}")
    return sizes


def bench_exit_code(result: BenchResult) -> int:
    if result.build_failure is not None or result.load_error is not None:
        return ExitCode.USER_CODE_ERROR
    if result.wrong_answer is not None:
        return ExitCode.FAILURES
    return ExitCode.SUCCESS


def perf_lines(result: BenchResult) -> Iterator[Text]:
    """`cstudy test --perf`: the verdict line (or why there is none) and the warnings."""
    lines = BenchReportLines(result)
    yield from lines.failure()
    yield from lines.verdict()
    yield from lines.warnings()


def verdict_line(time: GrowthVerdict, analysis: TargetAnalysis | None) -> Text:
    """`verdict   optimal: matches hash-map, 1.17x at n=1e5 · confidence high (...)`."""
    line = Text(LABEL.format("verdict"), style="bold")
    line.append(f"{time.verdict}: {time.message} · confidence {time.confidence}")
    if analysis is not None and analysis.time is not None:
        spread = round(analysis.max_spread * PERCENT)
        line.append(f" (spread {spread}%, R^2 {analysis.time.fit.r2:.3f})", style="dim")
    return line


class BenchReportLines:
    def __init__(self, result: BenchResult) -> None:
        self._result = result

    def lines(self) -> Iterator[Text]:
        result = self._result
        yield Text(self._header(), style="bold")
        yield Text("")
        if result.build_failure is not None or result.load_error is not None:
            yield from self.failure()
            return
        yield from _LadderTable(result).lines()
        yield Text("")
        yield from self.verdict()
        yield from self._details()
        yield from self.warnings()

    def failure(self) -> Iterator[Text]:
        """Why the user's code did not run: build diagnostics or the load error."""
        result = self._result
        if result.build_failure is not None:
            yield Text("BUILD FAILED", style="bold red")
            yield from (Text(line) for line in result.build_failure.diagnostics)
        if result.load_error is not None:
            error = result.load_error
            yield Text(f"ERROR     load: {error.type}: {error.message}", style="bold red")

    def verdict(self) -> Iterator[Text]:
        """The verdict line, or the wrong answer that stopped the judging."""
        result = self._result
        if result.wrong_answer is not None:
            wrong = result.wrong_answer
            message = f"wrong answer at n={size_text(wrong.size)}: {wrong.detail}"
            yield Text(f"{LABEL.format('FAIL')}{message}", style="bold red")
        elif result.verdict is not None:
            user = result.measured.user if result.measured else None
            yield verdict_line(result.verdict.time, user)

    def warnings(self) -> Iterator[Text]:
        for warning in self._result.warnings:
            yield Text(f"{LABEL.format('warning')}{warning}", style="yellow")

    def _header(self) -> str:
        plan = self._result.plan
        machine = self._result.machine
        sizes = f"{size_text(plan.sizes[0])}..{size_text(plan.sizes[-1])}" if plan.sizes else "-"
        load = f"{machine.load_1m:.1f}" if machine.load_1m is not None else "unknown"
        parts = [
            plan.meta.slug,
            plan.language,
            f"sizes {sizes}",
            f"reps {plan.reps}",
            f"power {machine.power}",
            f"load {load}",
        ]
        return " · ".join(parts)

    def _details(self) -> Iterator[Text]:
        result = self._result
        if result.verdict is None:
            return
        yield _space_line(result.verdict.space)
        if result.history is not None:
            yield _history_line(result.history)


def _space_line(space: SpaceVerdict) -> Text:
    message = space.message.removeprefix("space ")
    return Text(f"{LABEL.format('space')}{message} · confidence {space.confidence}")


def _history_line(history: History) -> Text:
    change = round(abs(history.change) * PERCENT)
    direction = "faster" if history.change < 0 else "slower"
    trend = "same speed" if change == 0 else f"{change}% {direction}"
    best = (
        f"best previous {duration_text(history.best_previous_ns)} at n={size_text(history.size)} "
        f"({history.best_ran_at.date().isoformat()})"
    )
    rank = f"{_ordinal(history.rank)} of {history.runs} runs"
    return Text(f"{LABEL.format('history')}{best} · now {trend} · {rank}")


def _ordinal(number: int) -> str:
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    suffix = "th" if 10 <= number % 100 <= 20 else suffixes.get(number % 10, "th")
    return f"{number}{suffix}"


class _LadderTable:
    """TARGET, DECLARED, one column per size, SLOPE, BAND, MEMORY."""

    def __init__(self, result: BenchResult) -> None:
        self._result = result

    def lines(self) -> Iterator[Text]:
        rows = [self._head(), *self._rows()]
        widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
        for index, row in enumerate(rows):
            cells = [cell.ljust(width) for cell, width in zip(row, widths, strict=True)]
            yield Text("  ".join(cells).rstrip(), style="bold" if index == 0 else "")

    def _head(self) -> list[str]:
        sizes = [f"n={size_text(size)}" for size in self._result.plan.sizes]
        return ["TARGET", "DECLARED", *sizes, "SLOPE", "BAND", "MEMORY"]

    def _rows(self) -> Iterator[list[str]]:
        measured = self._result.measured
        if measured is None:
            return
        declared = {a.id: a.time for a in self._result.plan.meta.approaches}
        for analysis in measured.references:
            yield self._row(analysis.target_id, declared.get(analysis.target_id, ""), analysis)
        if measured.user is not None:
            yield self._row(USER_LABEL, "", measured.user)

    def _row(self, label: str, declared: str, analysis: TargetAnalysis) -> list[str]:
        cells = [self._cell(analysis, size) for size in self._result.plan.sizes]
        time, memory = analysis.time, analysis.memory
        slope = f"{time.fit.slope:.2f}" if time else "-"
        band = time.band.label if time else "-"
        return [label, declared, *cells, slope, band, memory.band.value if memory else "-"]

    def _cell(self, analysis: TargetAnalysis, size: int) -> str:
        stats = analysis.series.at(size)
        if stats is None:
            return "-"
        if stats.status is SizeStatus.COMPLETED and stats.median_ns is not None:
            return duration_text(stats.median_ns)
        return _CELLS.get(stats.status, "-")
