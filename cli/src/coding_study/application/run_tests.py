"""`cstudy test`: run the user's code against the cases and judge it
(docs/specs/cli.md#cstudy-test).

Progressive problems run the cases of the unlocked levels (or up to `--level`); a run that passes
every unlocked level unlocks the next one and rewrites the statement to show it. Concurrent
problems run their sequential cases, then every stress case N times per variant
(docs/specs/cli.md#concurrent-problems). Other problems with `--stress N` also run N generated
inputs whose expected values are the oracle's outputs (docs/specs/cli.md#oracle-inputs).

A run is planned, which checks its options and does nothing else, then carried out. A listener
hears the build end and each case and stress run as the runner reports it, judged as the whole run
is judged at its end (docs/specs/cli.md#event-stream).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol

from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.case_materialization import CaseMaterializer, python_approaches
from coding_study.application.comparison import problem_comparator
from coding_study.application.environment import Environment
from coding_study.application.language_runs import CodeRun, LanguageRun
from coding_study.application.ports import BuildFailed, PrepareResult, ProgressNotice, UserCode
from coding_study.application.run_bench import (
    PERF_REPS,
    BenchOptions,
    BenchResult,
    RunBenchRequest,
    run_bench,
)
from coding_study.application.statement_file import write_statement
from coding_study.application.stress_judging import stress_judging, without_stress
from coding_study.application.time_limits import (
    TimeLimitFlags,
    TimeLimitRequest,
    requested_time_limit,
    resolve_time_limits,
)
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt, RunRecord
from coding_study.domain.comparators import Comparator
from coding_study.domain.debugging import DebugRequest, DebugSession, debug_session
from coding_study.domain.diagnostics import (
    Diagnostic,
    DiagnosticParser,
    DiagnosticSource,
    SolutionFiles,
    in_solution_files,
    solution_load_diagnostic,
)
from coding_study.domain.diagnostics_go import GoReport
from coding_study.domain.diagnostics_javac import JavacReport
from coding_study.domain.diagnostics_kotlinc import KotlincReport
from coding_study.domain.diagnostics_rustc import RustcReport
from coding_study.domain.diagnostics_tsc import CURRENT_DIRECTORY, TscReport
from coding_study.domain.errors import UsageError
from coding_study.domain.generated_cases import OracleInput, oracle_approach, oracle_inputs
from coding_study.domain.judging import (
    CaseVerdict,
    Judgement,
    RunnableCase,
    Tally,
    failed_to_run,
    judge,
    with_oracle,
    with_stress,
    with_time_limits,
)
from coding_study.domain.levels import LevelRun, cases_up_to, level_run
from coding_study.domain.problem import Language, Problem, ProblemKind, ProblemMeta
from coding_study.domain.problem_files import GENERATOR_FILE
from coding_study.domain.runs import CaseReport, JobReport
from coding_study.domain.stress_runs import PlannedRun, StressSelection, plan_runs
from coding_study.domain.stress_verdict import (
    StressJudging,
    StressRunResult,
    judge_run,
    judge_stress,
)
from coding_study.domain.time_limits import TimeLimit, TimeLimits

MILLISECONDS_PER_SECOND = 1000
DEFAULT_ORACLE_SEED = 1
STRESS_SKIPPED_NOTICE = "stress runs are skipped while debugging"
BUILD_REPORTS: Mapping[Language, DiagnosticParser | None] = {
    Language.PYTHON: None,
    Language.TYPESCRIPT: TscReport(CURRENT_DIRECTORY),
    Language.JAVA: JavacReport(),
    Language.KOTLIN: KotlincReport(),
    Language.GO: GoReport(),
    Language.RUST: RustcReport(),
}
"""How to read a failed build of a single file, whose paths are the directory the tool ran in or
absolute; TypeScript builds nothing but `--typecheck`. None: each line is a diagnostic without a
place, as it is for a report the language's parser finds nothing in."""


@dataclass(frozen=True, slots=True)
class RunTestsRequest:
    slug: str | None = None
    language: Language | None = None
    case_ids: tuple[str, ...] = ()
    """Only these cases; empty runs every case."""
    typecheck: bool = False
    time_limits: TimeLimitFlags = field(default_factory=TimeLimitFlags)
    level: int | None = None
    """Progressive problems: run levels 1 to `level`; None runs every unlocked level."""
    stress: StressSelection = field(default_factory=StressSelection)
    """`--stress N` and `--seed S`: stress runs of a concurrent problem, else oracle inputs."""
    debug: DebugRequest | None = None
    """`--debug`: judge the run under an IDE debugger (`debugging.py`). Time limits are off, a
    concurrent problem's stress runs are skipped, and the run is not recorded: pauses would
    distort its timings, and it leaves stress runs out."""


@dataclass(frozen=True, slots=True)
class RunTestsResult:
    meta: ProblemMeta
    attempt: Attempt
    """As stored after this run."""
    language: Language
    cases: tuple[RunnableCase, ...]
    comparator: Comparator
    code_run: CodeRun
    judgement: Judgement | None
    """None when the code did not build."""
    ran_at: datetime
    duration_seconds: float
    every_case: bool = True
    """False when `--case` or the levels selected some cases."""
    time_limits: TimeLimits | None = None
    """None when time limits were off or could not apply."""
    levels: LevelRun | None = None
    """Progressive problems only."""
    stress_plan: tuple[PlannedRun, ...] = ()
    """Concurrent problems: every planned (stress case, variant, run)."""
    oracle: "OracleStress | None" = None
    """Other problems with `--stress N`: the generated inputs checked against the oracle."""
    debug: DebugSession | None = None
    """Set for a debug run, which is not recorded."""
    diagnostics: tuple[Diagnostic, ...] = ()
    """Where the code did not build or load (docs/specs/cli.md#diagnostics)."""

    @property
    def build_failure(self) -> BuildFailed | None:
        return self.code_run.build_failure

    @property
    def case_total(self) -> int:
        """Cases, oracle inputs, and one per (stress case, variant)."""
        oracle_inputs = len(self.oracle.inputs) if self.oracle else 0
        return len(self.cases) + oracle_inputs + self.stress_verdict_count

    @property
    def stress_verdict_count(self) -> int:
        """Each (stress case, variant) counts as one case."""
        return len({(run.case.id, run.variant) for run in self.stress_plan})

    @property
    def tally(self) -> Tally:
        """What `test_runs` stores: the problem's own cases. Oracle inputs are an extra check,
        like `--perf`: they can fail the run, but `cstudy done` judges the problem's cases."""
        judgement = self.case_judgement
        if judgement:
            return judgement.tally()
        return failed_to_run(len(self.cases) + self.stress_verdict_count)

    @property
    def passed(self) -> bool:
        """Every case and every oracle input passed."""
        return self.judgement is not None and self.judgement.passed

    @property
    def cases_passed(self) -> bool:
        """Every case of the problem passed, whatever the oracle inputs did."""
        judgement = self.case_judgement
        return judgement is not None and judgement.passed

    @property
    def case_judgement(self) -> Judgement | None:
        """The judgement without the oracle inputs."""
        judgement = self.judgement
        if judgement is None or self.oracle is None:
            return judgement
        oracle_ids = self.oracle.case_ids
        return replace(
            judgement,
            case_count=judgement.case_count - len(oracle_ids),
            verdicts=tuple(
                verdict for verdict in judgement.verdicts if verdict.case.id not in oracle_ids
            ),
        )


@dataclass(frozen=True, slots=True)
class OracleStress:
    approach: str
    """The `oracle: true` approach whose Python outputs are the expected values."""
    inputs: tuple[OracleInput, ...]

    @property
    def case_ids(self) -> frozenset[str]:
        return frozenset(found.case_id for found in self.inputs)


class RunTestsListener(Protocol):
    """Told when the build ends, then of each case and stress run as the runner starts it and as
    soon as the runner reports its outcome, judged."""

    def build_ended(self, seconds: float, note: str | None) -> None:
        """Only for a language or option that builds: `note` is None when the build failed."""
        ...

    def case_started(self, case: RunnableCase) -> None: ...

    def case_judged(self, verdict: CaseVerdict) -> None:
        """Judged by the comparator: time limits are judged after the run."""
        ...

    def stress_run_started(self, planned: PlannedRun) -> None: ...

    def stress_run_judged(self, planned: PlannedRun, result: StressRunResult) -> None: ...


@dataclass(frozen=True, slots=True)
class RunTestsPlan:
    """A run whose options are checked, before any of its work: nothing is built, computed or
    run yet."""

    request: RunTestsRequest
    started: float
    """On the environment's monotonic clock."""
    attempt: Attempt
    language: Language
    problem: Problem
    debug: DebugSession | None
    oracle: OracleStress | None
    levels: LevelRun | None
    covered: Problem
    """The cases of the levels the run covers."""
    selected: Problem
    """Those that `--case` selects."""
    stress_plan: tuple[PlannedRun, ...]
    """Every planned stress run, also those a debug run skips."""
    time_limit: TimeLimit | None
    """The time limit the run asks for; None when time limits are off."""
    listener: RunTestsListener | None = None

    @property
    def meta(self) -> ProblemMeta:
        return self.problem.meta


def run_tests(
    environment: Environment, request: RunTestsRequest, notify: ProgressNotice
) -> RunTestsResult:
    return run_planned_tests(environment, plan_tests(environment, request), notify)


def plan_tests(environment: Environment, request: RunTestsRequest) -> RunTestsPlan:
    """Raises UsageError without an attempt in progress, for a level still locked, a `--case`
    that names no case, or `--stress` or `--seed` that the problem cannot take."""
    started = environment.clock.monotonic()
    attempt = find_attempt(environment.progress, request.slug, request.language)
    language = autograded_language(attempt)
    debug = resolve_debug_session(request.debug, language)
    problem = environment.problems.load(attempt.slug)
    oracle = _oracle_stress(environment, problem, request.stress)
    levels = _level_run(problem, attempt.level_unlocked, request.level)
    covered = _up_to_level(problem, levels)
    selected = _selected_cases(covered, request.case_ids)
    time_limit = requested_time_limit(environment.config, problem.meta, request.time_limits)
    return RunTestsPlan(
        request=request,
        started=started,
        attempt=attempt,
        language=language,
        problem=problem,
        debug=debug,
        oracle=oracle,
        levels=levels,
        covered=covered,
        selected=selected,
        stress_plan=plan_runs(selected, language, request.stress),
        time_limit=time_limit if debug is None else None,
    )


def run_planned_tests(
    environment: Environment, plan: RunTestsPlan, notify: ProgressNotice
) -> RunTestsResult:
    clock = environment.clock
    request, meta, language, debug = plan.request, plan.meta, plan.language, plan.debug
    oracle = plan.oracle
    materializer = CaseMaterializer(environment, notify)
    cases = materializer.runnable_cases(without_stress(plan.selected))
    oracle_cases = materializer.oracle_cases(meta, oracle.approach, oracle.inputs) if oracle else ()
    stress_plan = plan.stress_plan if debug is None else _skipped_stress_runs(plan, notify)
    comparator = problem_comparator(environment, meta)
    judging = _Judging(environment, plan.problem, comparator)
    run = LanguageRun(environment, meta, language)
    job = run.user_job((*cases, *oracle_cases), stress_plan)
    listener = plan.listener
    live = _LiveJudge((*cases, *oracle_cases), stress_plan, judging, listener) if listener else None
    code_run = run.run(UserCode(meta, request.typecheck, debug), [job], notify, listener=live)
    judgement: Judgement | None = None
    limits: TimeLimits | None = None
    if code_run.report is not None:
        report = code_run.report.job(meta.slug)
        judgement = judge(cases, report, comparator)
        if judgement.load_error is None and debug is None:
            limit_request = TimeLimitRequest(
                without_stress(plan.problem),
                language,
                code_run.report.runner.runtime,
                request.time_limits,
            )
            limits = resolve_time_limits(environment, limit_request, notify)
        if limits is not None:
            judgement = with_time_limits(judgement, limits)
        if oracle_cases:
            judgement = with_oracle(judgement, judge(oracle_cases, report, comparator))
        if stress_plan:
            judgement = with_stress(judgement, judge_stress(stress_plan, report, judging.stress()))
    result = RunTestsResult(
        meta=meta,
        attempt=plan.attempt,
        language=language,
        cases=cases,
        comparator=comparator,
        code_run=code_run,
        judgement=judgement,
        ran_at=clock.now(),
        duration_seconds=clock.monotonic() - plan.started,
        every_case=not request.case_ids and len(plan.covered.cases) == len(plan.problem.cases),
        time_limits=limits,
        levels=plan.levels,
        stress_plan=stress_plan,
        oracle=oracle,
        debug=debug,
        diagnostics=_diagnostics(code_run, judgement, solution_files(meta, language), language),
    )
    if debug is not None:
        return result
    result = replace(result, attempt=_record(environment, result))
    if request.case_ids:
        return result
    return _unlock(environment, plan.problem, result)


def perf_check(
    environment: Environment, result: RunTestsResult, notify: ProgressNotice
) -> BenchResult | None:
    """`cstudy test --perf`: a short bench, stored as a bench run, after a pass of every case
    (docs/specs/performance-analysis.md#integration); None when a case did not pass or `--case`
    or `--level` selected some."""
    if not (result.passed and result.every_case):
        return None
    request = RunBenchRequest(result.meta.slug, result.language, BenchOptions(reps=PERF_REPS))
    return run_bench(environment, request, notify)


def resolve_debug_session(request: DebugRequest | None, language: Language) -> DebugSession | None:
    if request is None:
        return None
    try:
        return debug_session(request, language)
    except ValueError as error:
        raise UsageError(str(error)) from None


def _skipped_stress_runs(plan: RunTestsPlan, notify: ProgressNotice) -> tuple[()]:
    """A runner paused at a breakpoint would fail the deadlines of stress runs: none run while
    debugging."""
    if plan.stress_plan:
        notify(STRESS_SKIPPED_NOTICE)
    return ()


class _Judging:
    """What judging a run's cases and stress runs needs. Stress judging is loaded once, when the
    first stress run is judged: a broken stress_checker.py stops only a run whose code ran."""

    def __init__(self, environment: Environment, problem: Problem, comparator: Comparator) -> None:
        self._environment = environment
        self._problem = problem
        self.comparator = comparator
        self._stress: StressJudging | None = None

    def stress(self) -> StressJudging:
        if self._stress is None:
            self._stress = stress_judging(self._environment, self._problem, self.comparator)
        return self._stress


class _LiveJudge:
    """Judges each case and stress run the runner reports, as `run_planned_tests` judges them
    all at the end, for a `RunTestsListener`."""

    def __init__(
        self,
        cases: Sequence[RunnableCase],
        stress_plan: Sequence[PlannedRun],
        judging: _Judging,
        listener: RunTestsListener,
    ) -> None:
        self._cases = {case.id: case for case in cases}
        self._runs = {planned.run_id: planned for planned in stress_plan}
        self._judging = judging
        self._listener = listener

    def build_ended(self, seconds: float, prepared: PrepareResult) -> None:
        if isinstance(prepared, BuildFailed):
            self._listener.build_ended(seconds, None)
        elif prepared.build_note is not None:
            self._listener.build_ended(seconds, prepared.build_note)

    def case_started(self, job_id: str, case_id: str) -> None:
        if case_id in self._cases:
            self._listener.case_started(self._cases[case_id])
        elif case_id in self._runs:
            self._listener.stress_run_started(self._runs[case_id])

    def case_finished(self, job_id: str, report: CaseReport) -> None:
        case_id = report.case_id
        if case_id in self._cases:
            case = self._cases[case_id]
            judged = judge((case,), JobReport(job_id, (report,)), self._judging.comparator)
            self._listener.case_judged(judged.verdicts[0])
        elif case_id in self._runs:
            planned = self._runs[case_id]
            result = judge_run(planned, report.outcome, self._judging.stress())
            self._listener.stress_run_judged(planned, result)


def solution_files(meta: ProblemMeta, language: Language) -> SolutionFiles:
    """The user file, and on the JVM and in Go the package `cstudy test --watch` watches."""
    user_file = layout.stub_path(meta, language)
    watched = layout.watch_path(meta, language)
    return SolutionFiles(user_file, watched if watched != user_file else None)


def _diagnostics(
    code_run: CodeRun, judgement: Judgement | None, files: SolutionFiles, language: Language
) -> tuple[Diagnostic, ...]:
    """Where the code did not build or load (docs/specs/cli.md#diagnostics): each line of a failed
    build, read by its tool's parser when it has one, or the load error."""
    failure = code_run.build_failure
    if failure is not None:
        found = _build_diagnostics(failure, language)
        return tuple(in_solution_files(diagnostic, files) for diagnostic in found)
    load_error = judgement.load_error if judgement else None
    return (solution_load_diagnostic(load_error, files),) if load_error else ()


def _build_diagnostics(failure: BuildFailed, language: Language) -> tuple[Diagnostic, ...]:
    parser = BUILD_REPORTS[language]
    found = parser.parse("\n".join(failure.diagnostics)) if parser else ()
    return found or tuple(Diagnostic(line, DiagnosticSource.BUILD) for line in failure.diagnostics)


def _oracle_stress(
    environment: Environment, problem: Problem, stress: StressSelection
) -> OracleStress | None:
    """`--stress N` on a problem that is not concurrent: N generated inputs from seed `--seed`
    (default 1). Raises UsageError when the problem has none to offer."""
    meta = problem.meta
    if meta.kind is ProblemKind.CONCURRENT:
        return None
    if stress.runs is None:
        if stress.seed is not None:
            raise UsageError(f"--seed needs --stress N for {meta.slug} (not a concurrent problem)")
        return None
    if meta.kind is ProblemKind.PROGRESSIVE:
        raise UsageError(f"--stress has no oracle inputs for progressive problems like {meta.slug}")
    needs = "--stress needs generator.py and an oracle approach with a Python reference"
    if environment.files.read_text(meta.slug, GENERATOR_FILE) is None:
        raise UsageError(f"{needs}; {meta.slug} has no generator.py")
    oracle = oracle_approach(meta)
    if oracle is None or oracle not in python_approaches(environment, meta):
        raise UsageError(f"{needs}; {meta.slug} has no oracle with a Python reference")
    first_seed = stress.seed if stress.seed is not None else DEFAULT_ORACLE_SEED
    return OracleStress(oracle, oracle_inputs(stress.runs, first_seed))


def _level_run(problem: Problem, unlocked: int | None, requested: int | None) -> LevelRun | None:
    try:
        return level_run(problem.meta, unlocked, requested)
    except ValueError as error:
        raise UsageError(str(error)) from None


def _up_to_level(problem: Problem, levels: LevelRun | None) -> Problem:
    """The cases of the levels a run covers; every case when the problem has no levels."""
    if levels is None:
        return problem
    return replace(problem, cases=cases_up_to(problem.cases, levels.ran_up_to))


def _selected_cases(problem: Problem, case_ids: tuple[str, ...]) -> Problem:
    if not case_ids:
        return problem
    known = {case.id for case in problem.cases}
    unknown = next((case_id for case_id in case_ids if case_id not in known), None)
    if unknown is not None:
        listed = ", ".join(case.id for case in problem.cases)
        raise UsageError(f'no case "{unknown}" in {_scope(problem)}; cases: {listed}')
    return replace(problem, cases=tuple(case for case in problem.cases if case.id in case_ids))


def _scope(problem: Problem) -> str:
    levels = {case.level for case in problem.cases if case.level is not None}
    slug = problem.meta.slug
    return f"{slug} levels 1 to {max(levels)}" if levels else slug


def _unlock(environment: Environment, problem: Problem, result: RunTestsResult) -> RunTestsResult:
    """A pass of every unlocked level opens the next one and shows it in the statement."""
    if result.levels is None or not result.passed:
        return result
    levels = result.levels.after_passing()
    if not levels.newly_unlocked:
        return result
    attempt = replace(result.attempt, level_unlocked=levels.unlocked)
    environment.progress.update_attempt(attempt)
    write_statement(environment, problem, levels.unlocked)
    return replace(result, attempt=attempt, levels=levels)


def _record(environment: Environment, result: RunTestsResult) -> Attempt:
    """Stores the run; the first full pass also sets the attempt's `first_pass_at`."""
    attempt = result.attempt
    watched = layout.watch_path(result.meta, result.language)
    environment.progress.add_test_run(
        RunRecord(
            attempt_id=attempt.id,
            ran_at=result.ran_at,
            code_hash=environment.workspace.content_hash(watched),
            tally=result.tally,
            duration_ms=round(result.duration_seconds * MILLISECONDS_PER_SECOND),
            time_limit=str(result.time_limits.limit) if result.time_limits else None,
        )
    )
    if result.every_case and result.cases_passed and attempt.first_pass_at is None:
        attempt = replace(attempt, first_pass_at=result.ran_at)
        environment.progress.update_attempt(attempt)
    return attempt
