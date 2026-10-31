"""`cstudy test` (docs/specs/cli.md#cstudy-test).

Visible cases are always listed; passing hidden cases collapse into a count unless `--all`;
failing hidden cases show input, expected and actual (PRD Q10). Progressive problems name the
levels a run covered and the level it unlocked. Concurrent problems print one line per stress
case and variant, with up to 3 failing runs. Oracle inputs (`--stress N` on other problems) show
their 3 smallest failures and collapse the rest into counts.

`--debug` runs the same judged run with the runner waiting for an IDE debugger. Its ready line goes
to standard error as plain text, like every notice of a `--json` run, so IDE tasks can match it; the
report shows no durations, because pauses at breakpoints would be part of them.

`--events` on a project problem writes the run as JSON events instead of the report
(docs/specs/cli.md#event-stream).
"""

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Annotated, NoReturn, Protocol

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application import run_tests as use_case
from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.environment import Environment
from coding_study.application.project_events import stream_project_tests
from coding_study.application.project_testing import (
    ProjectTestRequest,
    ProjectTestResult,
    is_project_attempt,
)
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.application.run_bench import (
    PERF_REPS,
    BenchOptions,
    RunBenchRequest,
    run_bench,
)
from coding_study.application.time_limits import TimeLimitFlags
from coding_study.domain import layout
from coding_study.domain.debugging import DebugRequest
from coding_study.domain.errors import UsageError
from coding_study.domain.generated_cases import OracleInput
from coding_study.domain.judging import CaseStatus, CaseVerdict
from coding_study.domain.problem import Language
from coding_study.domain.runs import UserError
from coding_study.domain.stress_runs import StressSelection
from coding_study.domain.stress_verdict import StressVerdict
from coding_study.domain.time_limits import (
    NANOSECONDS_PER_MILLISECOND,
    CaseLimit,
    parse_time_limit,
)
from coding_study.entrypoints.commands._events import (
    RunSummary,
    require_events_alone,
    write_events,
)
from coding_study.entrypoints.commands.bench import bench_exit_code, perf_lines
from coding_study.entrypoints.commands.project_documents import project_test_document
from coding_study.entrypoints.commands.project_test import (
    ProjectTestOptions,
    ProjectTestSession,
    require_project_options,
)
from coding_study.entrypoints.commands.report_text import (
    INDENT,
    LABEL_WIDTH,
    STATUS_STYLES,
    STATUS_WIDTH,
    case_details,
    clock_text,
    detail_line,
    duration_text,
    error_text,
    levels_text,
    trace_lines,
)
from coding_study.entrypoints.commands.run_document import run_document
from coding_study.entrypoints.shared import (
    ERROR_EXIT_CODES,
    OPTIONAL_TARGET_HELP,
    ExitCode,
    add_command,
    command_environ,
    console,
    optional_value_command,
    print_error,
)

NAME = "test"
MIN_ID_WIDTH = 6
DONE_HINT = "all passed. Next: cstudy done --rating easy|ok|hard"
STRESS_EVIDENCE = "stress runs found no race (not a proof of thread safety)"
MAX_STRESS_RUNS = 100
SHOWN_ORACLE_FAILURES = 3
TIMES = "\N{MULTIPLICATION SIGN}"
SUBSET_PASSED = "all selected cases passed"
DEBUG_PASSED = "all passed (debug run: not recorded; cstudy test records the run)"
STATEMENT_LABEL = "statement  "
MAX_PORT = 65535
TIME_LIMIT_OPTION = "--time-limit"
_SUMMARY_LABELS = (
    (CaseStatus.FAIL, "failed", "failed"),
    (CaseStatus.INVALID, "invalid", "invalid"),
    (CaseStatus.ERROR, "error", "errors"),
    (CaseStatus.TIMEOUT, "timeout", "timeouts"),
    (CaseStatus.STALLED, "stalled", "stalled"),
    (CaseStatus.TLE, "tle", "tle"),
    (CaseStatus.NOT_RUN, "not run", "not run"),
)


def register(app: typer.Typer) -> None:
    """A bare `--time-limit` means "on, with the resolved value"."""
    add_command(app, run_tests, NAME, optional_value_command(TIME_LIMIT_OPTION))


def run_tests(
    context: typer.Context,
    slug: Annotated[
        str | None,
        typer.Argument(help=OPTIONAL_TARGET_HELP),
    ] = None,
    language: Annotated[
        Language | None, typer.Option("--lang", help="Language; default: the attempt's.")
    ] = None,
    watch: Annotated[
        bool, typer.Option("--watch", help="Re-run on every save of the user file.")
    ] = False,
    case: Annotated[
        list[str] | None, typer.Option("--case", metavar="ID", help="Run only these cases.")
    ] = None,
    show_all: Annotated[
        bool, typer.Option("--all", help="Print every case, including passing hidden ones.")
    ] = False,
    typecheck: Annotated[
        bool, typer.Option("--typecheck", help="TypeScript: also run tsc --noEmit.")
    ] = False,
    time_limit: Annotated[
        str | None,
        typer.Option(
            TIME_LIMIT_OPTION,
            metavar="[=VALUE]",
            help="Enable time limits; VALUE is a factor (5x) or a duration (1500ms).",
        ),
    ] = None,
    no_time_limit: Annotated[
        bool,
        typer.Option("--no-time-limit", help="Disable time limits even if config enables them."),
    ] = False,
    level: Annotated[
        int | None,
        typer.Option(
            "--level", metavar="N", min=1, help="Progressive: run levels 1 to N (unlocked only)."
        ),
    ] = None,
    perf: Annotated[
        bool, typer.Option("--perf", help="After all cases pass, run a short bench.")
    ] = False,
    stress: Annotated[
        int | None,
        typer.Option(
            "--stress",
            metavar="N",
            min=1,
            max=MAX_STRESS_RUNS,
            help=(
                "Concurrent problems: runs per stress case and variant (default 3); "
                "others: N generated inputs checked against the oracle."
            ),
        ),
    ] = None,
    seed: Annotated[
        int | None,
        typer.Option(
            "--seed",
            metavar="S",
            help="Base seed: run r (or oracle input r) uses S + r.",
        ),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the report.")
    ] = False,
    events: Annotated[
        bool,
        typer.Option("--events", help="Project problems: the run as JSON events, one per line."),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Wait for an IDE debugger to attach to the runner (docs/specs/runners.md).",
        ),
    ] = False,
    debug_port: Annotated[
        int | None,
        typer.Option(
            "--debug-port",
            metavar="N",
            min=1,
            max=MAX_PORT,
            help="With --debug: the agent's port (python 5678, typescript 9229, java/kotlin 5005).",
        ),
    ] = None,
    debug_connect: Annotated[
        bool,
        typer.Option(
            "--debug-connect",
            help="With --debug, java and kotlin: connect to an IDE that is already listening.",
        ),
    ] = False,
) -> None:
    """Run the user's code against the cases."""
    options = _Options(show_all, perf, as_json, debug)
    debug_request = _debug_request(
        _DebugOptions(debug, debug_port, debug_connect),
        _given(
            {
                "--watch": watch,
                "--perf": perf,
                "--json": as_json,
                "--stress": stress is not None,
                "--seed": seed is not None,
                "--time-limit": time_limit is not None,
            }
        ),
    )
    _require_text_for(options, watch)
    if events:
        require_events_alone(_given({"--json": as_json, "--watch": watch, "--debug": debug}))
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug, language), Path.cwd())
    if is_project_attempt(environment, target.slug, target.language):
        require_project_options(
            _given(
                {
                    "--perf": perf,
                    "--stress": stress is not None,
                    "--seed": seed is not None,
                    "--time-limit": time_limit is not None,
                    "--debug-connect": debug_connect,
                }
            )
        )
        project_request = ProjectTestRequest(
            target.slug, target.language, tuple(case or ()), level, debug_request
        )
        if events:
            raise typer.Exit(_stream_project_tests(environment, project_request))
        project_options = ProjectTestOptions(as_json, debug)
        project = ProjectTestSession(
            environment, project_request, console(context), project_options
        )
        _run_session(project, watch)
    if events:
        raise UsageError("--events is for project problems")
    request = use_case.RunTestsRequest(
        target.slug,
        target.language,
        tuple(case or ()),
        typecheck,
        _time_limit_flags(time_limit, no_time_limit),
        level,
        StressSelection(stress, seed),
        debug_request,
    )
    _run_session(_Session(environment, request, console(context), options), watch)


def _stream_project_tests(environment: Environment, request: ProjectTestRequest) -> int:
    return write_events(
        lambda emit: stream_project_tests(environment, request, emit), _project_summary
    )


def _project_summary(result: ProjectTestResult) -> RunSummary:
    exit_code = ExitCode.SUCCESS if result.passed else ExitCode.FAILURES
    return RunSummary(exit_code, project_test_document(result, exit_code))


class _RunSession(Protocol):
    def run(self) -> int: ...

    def watch(self) -> int: ...


def _run_session(session: _RunSession, watch: bool) -> NoReturn:
    """Runs once, or on every save with `--watch`, and exits with the last run's code."""
    try:
        raise typer.Exit(session.watch() if watch else session.run())
    except KeyboardInterrupt:
        raise typer.Exit(ExitCode.INTERRUPTED) from None


def _time_limit_flags(time_limit: str | None, no_time_limit: bool) -> TimeLimitFlags:
    """`time_limit` is "" for a bare `--time-limit`."""
    if time_limit is not None and no_time_limit:
        raise UsageError("--time-limit and --no-time-limit exclude each other")
    if no_time_limit:
        return TimeLimitFlags(enabled=False)
    if time_limit is None:
        return TimeLimitFlags()
    if not time_limit:
        return TimeLimitFlags(enabled=True)
    try:
        return TimeLimitFlags(enabled=True, value=parse_time_limit(time_limit))
    except ValueError as error:
        raise UsageError(str(error)) from None


@dataclass(frozen=True, slots=True)
class _Options:
    show_all: bool = False
    perf: bool = False
    """`--perf`: after a full pass, a short bench and its verdict line."""
    as_json: bool = False
    """`--json`: the run as one JSON document; notices go to standard error."""
    debug: bool = False
    """`--debug`: notices go to standard error too, where the ready line must be."""


@dataclass(frozen=True, slots=True)
class _DebugOptions:
    debug: bool
    port: int | None
    connect: bool


def _given(options: Mapping[str, bool]) -> tuple[str, ...]:
    """The options of this run that `--debug` cannot go with, as the user typed them: a paused
    runner would fail time limits and stress deadlines, a rerun would restart the debug session,
    and a JSON document or a bench has no use for a debugger."""
    return tuple(option for option, used in options.items() if used)


def _debug_request(options: _DebugOptions, excluded: tuple[str, ...]) -> DebugRequest | None:
    if not options.debug:
        needs = (("--debug-port", options.port is not None), ("--debug-connect", options.connect))
        for option, given in needs:
            if given:
                raise UsageError(f"{option} needs --debug")
        return None
    if excluded:
        raise UsageError(f"--debug excludes {', '.join(excluded)}")
    return DebugRequest(options.port, options.connect)


def _require_text_for(options: _Options, watch: bool) -> None:
    """`--watch` reprints and `--perf` adds a bench report: neither fits one JSON document."""
    if options.as_json and (watch or options.perf):
        raise UsageError("--json excludes --watch and --perf")


class _Session:
    def __init__(
        self,
        environment: Environment,
        request: use_case.RunTestsRequest,
        output: Console,
        options: _Options,
    ) -> None:
        self._environment = environment
        self._request = request
        self._output = output
        self._options = options

    def run(self) -> int:
        result = use_case.run_tests(self._environment, self._request, self._notice)
        exit_code = _exit_code(result)
        if self._options.as_json:
            typer.echo(json.dumps(run_document(result, exit_code), indent=2))
            return exit_code
        for line in _Report(result, self._options.show_all).lines():
            self._output.print(line)
        if self._options.perf and result.passed and result.every_case:
            return max(exit_code, self._perf(result))
        return exit_code

    def _perf(self, result: use_case.RunTestsResult) -> int:
        """docs/specs/performance-analysis.md#integration: `reps=3`, stored as a bench run."""
        options = BenchOptions(reps=PERF_REPS)
        request = RunBenchRequest(result.meta.slug, result.language, options)
        bench = run_bench(self._environment, request, self._notice)
        self._output.print(Text(""))
        for line in perf_lines(bench):
            self._output.print(line)
        return bench_exit_code(bench)

    def watch(self) -> int:
        """Run now and after every save, until interrupted; returns the last exit code."""
        watched = self._watched_path()
        exit_code = self._run_reporting_errors()
        for _ in self._environment.watcher.changes(watched):
            self._output.clear()
            exit_code = self._run_reporting_errors()
        return exit_code

    def _watched_path(self) -> Path:
        environment, request = self._environment, self._request
        attempt = find_attempt(environment.progress, request.slug, request.language)
        meta = environment.problems.load(attempt.slug).meta
        path = layout.watch_path(meta, autograded_language(attempt))
        return environment.workspace.absolute(path)

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


def _exit_code(result: use_case.RunTestsResult) -> int:
    judgement = result.judgement
    if judgement is None or judgement.load_error is not None:
        return ExitCode.USER_CODE_ERROR
    return ExitCode.SUCCESS if judgement.passed else ExitCode.FAILURES


class _Report:
    def __init__(self, result: use_case.RunTestsResult, show_all: bool) -> None:
        self._result = result
        self._show_all = show_all
        ids = [case.id for case in result.cases] + [run.case.id for run in result.stress_plan]
        oracle = result.oracle
        self._oracle_inputs = {found.case_id: found for found in oracle.inputs} if oracle else {}
        ids += list(self._oracle_inputs)
        longest = max((len(case_id) for case_id in ids), default=0)
        self._id_width = max(MIN_ID_WIDTH, longest + 2)

    def lines(self) -> Iterator[Text]:
        yield Text(self._header(), style="bold")
        code_run = self._result.code_run
        if code_run.build_note:
            yield Text(f"build  {code_run.build_seconds:.1f}s ({code_run.build_note})")
        yield Text("")
        yield from self._body()
        yield Text("")
        yield Text(self._summary())
        if self._result.passed:
            yield from self._passed()

    def _passed(self) -> Iterator[Text]:
        if self._result.debug is not None:
            yield Text(DEBUG_PASSED, style="green")
            return
        if self._result.stress_plan:
            yield Text(STRESS_EVIDENCE, style="dim")
        levels = self._result.levels
        if levels is not None and levels.newly_unlocked:
            unlocked, last = levels.unlocked, levels.progress.last
            title = levels.progress.title(unlocked)
            passed = f"level {levels.ran_up_to} passed"
            yield Text(f"{passed} · unlocked level {unlocked} of {last}: {title}", style="green")
            statement = layout.statement_path(self._result.meta.slug)
            yield Text(f"{STATEMENT_LABEL}{statement} (updated)")
            return
        yield Text(SUBSET_PASSED if self._is_subset() else DONE_HINT, style="green")

    def _header(self) -> str:
        cases = self._result.cases
        visible = sum(1 for case in cases if case.visible)
        generated = sum(1 for case in cases if case.generated)
        hidden = len(cases) - visible - generated
        noun = "case" if len(cases) == 1 else "cases"
        parts = [self._result.meta.slug, self._result.language]
        if self._result.debug is not None:
            parts.append("debug")
        levels = self._result.levels
        if levels is not None:
            parts.append(levels_text(levels.ran_up_to, levels.progress.last))
        if self._result.meta.concurrency is not None:
            parts += self._concurrent_counts(visible, hidden)
        else:
            parts.append(
                f"{len(cases)} {noun} ({visible} visible, {hidden} hidden, {generated} generated)"
            )
        if self._result.oracle is not None:
            parts.append(_oracle_counts(self._result.oracle.inputs))
        if self._result.time_limits is not None:
            parts.append(f"time limit {self._result.time_limits.limit}")
        attempt = self._result.attempt
        if attempt.time_limit_s is not None:
            elapsed = attempt.solve_time(self._result.ran_at)
            limit = timedelta(seconds=attempt.time_limit_s)
            parts.append(f"timer {clock_text(elapsed)} / {clock_text(limit)}")
        return " · ".join(parts)

    def _concurrent_counts(self, visible: int, hidden: int) -> list[str]:
        """`6 sequential (2 visible, 4 hidden) · 2 stress x 2 variants x 3 runs`, with the
        multiplication sign."""
        sequential = f"{visible + hidden} sequential ({visible} visible, {hidden} hidden)"
        plan = self._result.stress_plan
        if not plan:
            return [sequential]
        cases = len({run.case.id for run in plan})
        variants = len({run.variant for run in plan})
        runs = max(run.run for run in plan) + 1
        variant_noun = "variant" if variants == 1 else "variants"
        run_noun = "run" if runs == 1 else "runs"
        stress = f"{cases} stress {TIMES} {variants} {variant_noun} {TIMES} {runs} {run_noun}"
        return [sequential, stress]

    def _body(self) -> Iterator[Text]:
        result = self._result
        if result.build_failure is not None:
            yield Text("BUILD FAILED", style="bold red")
            yield from (Text(line) for line in result.build_failure.diagnostics)
            return
        judgement = result.judgement
        assert judgement is not None
        if judgement.load_error is not None:
            yield from self._load_error(judgement.load_error)
            return
        collapsed = 0
        oracle: list[CaseVerdict] = []
        for verdict in judgement.verdicts:
            if verdict.case.id in self._oracle_inputs:
                oracle.append(verdict)
            elif self._collapses(verdict):
                collapsed += 1
            else:
                yield from self._verdict(verdict)
        if collapsed:
            noun = "case" if collapsed == 1 else "cases"
            yield self._status_line(CaseStatus.PASS, f"{collapsed} hidden {noun}")
        yield from self._oracle(oracle)
        for stress in judgement.stress:
            yield from self._stress(stress)

    def _oracle(self, verdicts: list[CaseVerdict]) -> Iterator[Text]:
        """The smallest failing inputs first: they are the easiest to debug."""
        inputs = self._oracle_inputs
        failing = sorted(
            (verdict for verdict in verdicts if verdict.status is not CaseStatus.PASS),
            key=lambda verdict: (inputs[verdict.case.id].n, inputs[verdict.case.id].seed),
        )
        for verdict in failing[:SHOWN_ORACLE_FAILURES]:
            yield from self._oracle_verdict(verdict)
        hidden_failures = len(failing) - SHOWN_ORACLE_FAILURES
        if hidden_failures > 0:
            noun = "input" if hidden_failures == 1 else "inputs"
            yield Text(f"{INDENT}{hidden_failures} more oracle {noun} did not pass", style="dim")
        passed = len(verdicts) - len(failing)
        if passed:
            noun = "input" if passed == 1 else "inputs"
            yield self._status_line(CaseStatus.PASS, f"{passed} oracle {noun}")

    def _oracle_verdict(self, verdict: CaseVerdict) -> Iterator[Text]:
        line = self._status_line(verdict.status, verdict.case.id.ljust(self._id_width))
        line.append(f"oracle · n={self._oracle_inputs[verdict.case.id].n}", style="dim")
        yield line
        oracle = self._result.oracle
        assert oracle is not None
        comparator = self._result.comparator.label
        source = f"oracle {oracle.approach}"
        label = f"{comparator}, {source}" if comparator else source
        yield from (detail_line(name, value) for name, value in case_details(verdict, label))

    def _stress(self, verdict: StressVerdict) -> Iterator[Text]:
        """Stress cases are hidden but always printed: their scenario is the exercise."""
        line = self._status_line(verdict.status, verdict.case_id.ljust(self._id_width))
        line.append(_stress_label(verdict), style="dim")
        yield line
        for run in verdict.failures:
            reasons = run.reasons or ("failed",)
            yield Text(
                f"{INDENT}{' ' * self._id_width}run {run.run} · seed {run.seed}  {reasons[0]}"
            )
            for reason in reasons[1:]:
                yield Text(f"{INDENT}{' ' * self._id_width}{' ' * LABEL_WIDTH}{reason}")

    def _collapses(self, verdict: CaseVerdict) -> bool:
        is_hidden = not verdict.case.visible
        return is_hidden and verdict.status is CaseStatus.PASS and not self._show_all

    def _case_label(self, verdict: CaseVerdict) -> str:
        parts = [] if verdict.case.visible else ["hidden"]
        duration = verdict.duration_ns
        shows_durations = self._result.debug is None
        if verdict.status is CaseStatus.PASS and duration is not None and shows_durations:
            parts.append(duration_text(duration))
        if verdict.time_limit is not None and duration is not None:
            parts.append(f"{duration_text(duration)} > limit {_limit_text(verdict.time_limit)}")
        return " · ".join(parts)

    def _load_error(self, error: UserError) -> Iterator[Text]:
        line = self._status_line(CaseStatus.ERROR, "load".ljust(self._id_width))
        line.append(error_text(error))
        yield line
        yield from (Text(f"{INDENT}{' ' * self._id_width}{trace}") for trace in trace_lines(error))

    def _status_line(self, status: CaseStatus, rest: str) -> Text:
        line = Text(status.value.ljust(STATUS_WIDTH), style=STATUS_STYLES[status])
        line.append(rest)
        return line

    def _summary(self) -> str:
        result = self._result
        judgement = result.judgement
        total = result.case_total
        if judgement is None or judgement.load_error is not None:
            counts = [f"{total} {'error' if total == 1 else 'errors'}"]
            passed = 0
        else:
            passed = judgement.count(CaseStatus.PASS)
            counts = [
                f"{count} {singular if count == 1 else plural}"
                for status, singular, plural in _SUMMARY_LABELS
                if (count := judgement.count(status))
            ]
        parts = [f"{passed}/{total} passed", *counts]
        if result.debug is None:
            parts.append(f"total {result.duration_seconds:.1f}s")
        return " · ".join(parts)

    def _is_subset(self) -> bool:
        return not self._result.every_case

    def _verdict(self, verdict: CaseVerdict) -> Iterator[Text]:
        case = verdict.case
        line = self._status_line(verdict.status, case.id.ljust(self._id_width))
        line.append(self._case_label(verdict), style="dim")
        line.rstrip()
        yield line
        if verdict.status not in (CaseStatus.PASS, CaseStatus.TLE):
            details = case_details(verdict, self._result.comparator.label)
            yield from (detail_line(label, value) for label, value in details)


def _oracle_counts(inputs: tuple[OracleInput, ...]) -> str:
    """`20 oracle inputs (seeds 1-20)`, or `1 oracle input (seed 17)`."""
    first, last = inputs[0].seed, inputs[-1].seed
    if len(inputs) == 1:
        return f"1 oracle input (seed {first})"
    return f"{len(inputs)} oracle inputs (seeds {first}-{last})"


def _stress_label(verdict: StressVerdict) -> str:
    """`platform · 3/3 runs · median 38ms`, or `virtual · 1/3 runs passed`."""
    runs = len(verdict.runs)
    parts = [verdict.variant.value]
    if verdict.status is CaseStatus.PASS:
        parts.append(f"{runs}/{runs} runs")
        median = verdict.median_ms
        if median is not None:
            parts.append(f"median {duration_text(round(median * NANOSECONDS_PER_MILLISECOND))}")
    else:
        parts.append(f"{verdict.runs_passed}/{runs} runs passed")
    if verdict.status is CaseStatus.STALLED:
        parts.append(f"deadline {verdict.deadline_ms}ms")
    return " · ".join(parts)


def _limit_text(limit: CaseLimit) -> str:
    text = duration_text(round(limit.ms * NANOSECONDS_PER_MILLISECOND))
    return f"{text} ({limit.basis})" if limit.basis else text
