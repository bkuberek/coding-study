"""`cstudy bench` and `cstudy test --perf` (docs/specs/performance-analysis.md,
docs/specs/cli.md#cstudy-bench).

The user's code and every reference in the language run in one runner process on the same
generated inputs. The analysis places the user on the problem's ladder; the run is stored in
`bench_runs` with everything a later scheduling penalty needs (attempt, verdict, confidence).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

from coding_study.application.active_attempt import find_attempt
from coding_study.application.comparison import problem_comparator
from coding_study.application.environment import Environment
from coding_study.application.language_runs import LanguageRun
from coding_study.application.ports import BenchCode, BuildFailed, ProgressNotice
from coding_study.application.reference_runs import approaches_in
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt
from coding_study.domain.bench_records import (
    BenchRunRecord,
    MachineState,
    bench_seed,
    input_elements,
    max_batch,
)
from coding_study.domain.bench_runs import (
    USER_TARGET_ID,
    BenchInput,
    BenchJob,
    BenchReport,
    BenchRequest,
    BenchSettings,
    BenchTarget,
    TargetReport,
    Warmup,
)
from coding_study.domain.bench_stats import TargetAnalysis, analyze, summarize
from coding_study.domain.bench_verdict import (
    BenchVerdict,
    Conditions,
    Confidence,
    History,
    Ladder,
    Verdict,
    compare_history,
    judge,
)
from coding_study.domain.cases import Expected, JsonValue
from coding_study.domain.comparators import Comparator
from coding_study.domain.errors import ContentError, ContentIssue, UsageError
from coding_study.domain.generated_cases import generated_run_input
from coding_study.domain.judging import outcome_summary
from coding_study.domain.naming import symbol_names
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import ApproachRole, Language, Problem, ProblemMeta
from coding_study.domain.problem_files import GENERATOR_FILE, solution_file
from coding_study.domain.runs import UserError
from coding_study.domain.value_text import value_text

MIN_SAMPLE_NS = 20_000_000
PERF_REPS = 3
"""`cstudy test --perf` runs a short bench."""
SHOWN_VALUE_LENGTH = 80
WARMUPS: Mapping[Language, Warmup] = {
    Language.PYTHON: Warmup(1, 1, 0.05),
    Language.TYPESCRIPT: Warmup(3, 20, 0.05),
    Language.JAVA: Warmup(5, 20, 0.05),
    Language.KOTLIN: Warmup(5, 20, 0.05),
    Language.GO: Warmup(1, 3, 0.05),
    Language.RUST: Warmup(1, 3, 0.05),
}
"""docs/specs/performance-analysis.md#measurement; the check call counts as the first run."""
MEMORY_CAPS: Mapping[Language, Confidence] = {
    Language.PYTHON: Confidence.HIGH,
    Language.TYPESCRIPT: Confidence.LOW,
    Language.JAVA: Confidence.MEDIUM,
    Language.KOTLIN: Confidence.MEDIUM,
    Language.GO: Confidence.MEDIUM,
    Language.RUST: Confidence.HIGH,
}


@dataclass(frozen=True, slots=True)
class BenchOptions:
    sizes: tuple[int, ...] = ()
    """`--sizes`; empty: `perf.size_ladder`."""
    reps: int | None = None
    memory: bool | None = None
    """False for `--no-memory`; None: config `bench.memory`."""


@dataclass(frozen=True, slots=True)
class RunBenchRequest:
    slug: str | None = None
    language: Language | None = None
    options: BenchOptions = field(default_factory=BenchOptions)
    references_only: bool = False


@dataclass(frozen=True, slots=True)
class WrongAnswer:
    """The user's code failed on a bench input (exit code 1)."""

    size: int
    detail: str


@dataclass(frozen=True, slots=True)
class BenchPlan:
    problem: Problem
    language: Language
    approach_ids: tuple[str, ...]
    """References with a file in this language, in meta.yaml order."""
    expected_from: str | None
    """The reference whose outputs judge the user's; None when the user's code is not run."""
    request: BenchRequest

    @property
    def meta(self) -> ProblemMeta:
        return self.problem.meta

    @property
    def sizes(self) -> tuple[int, ...]:
        return tuple(bench_input.size for bench_input in self.request.job.inputs)

    @property
    def reps(self) -> int:
        return self.request.job.settings.reps

    @property
    def includes_user(self) -> bool:
        return any(target.target_id == USER_TARGET_ID for target in self.request.job.targets)


@dataclass(frozen=True, slots=True)
class Measured:
    report: BenchReport
    references: tuple[TargetAnalysis, ...]
    """Every reference that loaded, in meta.yaml order."""
    user: TargetAnalysis | None = None


@dataclass(frozen=True, slots=True)
class BenchResult:
    plan: BenchPlan
    machine: MachineState
    attempt: Attempt | None = None
    build_failure: BuildFailed | None = None
    measured: Measured | None = None
    load_error: UserError | None = None
    """The user's code did not load (exit code 2)."""
    wrong_answer: WrongAnswer | None = None
    verdict: BenchVerdict | None = None
    history: History | None = None
    warnings: tuple[str, ...] = ()


def run_bench(
    environment: Environment, request: RunBenchRequest, notify: ProgressNotice
) -> BenchResult:
    attempt, slug, language = _subject(environment, request)
    problem = environment.problems.load(slug)
    if problem.meta.concurrency is not None:
        raise UsageError("bench is not available for concurrent problems")
    plan = plan_bench(environment, problem, language, request)
    machine = environment.machine.snapshot()
    measured = measure(environment, plan, notify)
    if isinstance(measured, BuildFailed):
        return BenchResult(plan, machine, attempt, build_failure=measured)
    result = _Evaluation(environment, plan, machine).evaluate(measured)
    return _Recorder(environment, plan, attempt).record(result)


def plan_bench(
    environment: Environment, problem: Problem, language: Language, request: RunBenchRequest
) -> BenchPlan:
    meta = problem.meta
    approach_ids = approaches_in(environment, meta, language)
    expected_from = None if request.references_only else _expected_source(meta, approach_ids)
    sizes = tuple(sorted(set(request.options.sizes or meta.perf.size_ladder)))
    root = str(environment.root)
    names = symbol_names(meta.signature, language)
    targets = [
        BenchTarget(
            approach_id,
            layout.reference_target(meta, approach_id, language, root),
            names,
            emits_output=approach_id == expected_from,
        )
        for approach_id in approach_ids
    ]
    if not request.references_only:
        user = layout.user_target(meta, language, root)
        targets.insert(0, BenchTarget(USER_TARGET_ID, user, names, emits_output=True))
    job = BenchJob(
        job_id=meta.slug,
        kind=meta.kind,
        signature=meta.signature,
        targets=tuple(targets),
        inputs=_Inputs(environment, meta).for_sizes(sizes, language),
        settings=_settings(environment, meta, language, request.options),
        hang_guard_ms=max(
            resolve_hang_guard_ms(environment.config, None, meta.hang_guard_ms),
            meta.perf.budget_ms,
        ),
    )
    return BenchPlan(problem, language, approach_ids, expected_from, BenchRequest(job))


def measure(
    environment: Environment, plan: BenchPlan, notify: ProgressNotice
) -> Measured | BuildFailed:
    """One runner process for every target; BuildFailed when the user's code does not build."""
    run = LanguageRun(environment, plan.meta, plan.language)
    sources = run.references(plan.approach_ids).sources
    scope = BenchCode(plan.meta, sources, references_only=not plan.includes_user)
    prepared = environment.toolchains.runner(plan.language).prepare(scope, notify)
    if isinstance(prepared, BuildFailed):
        return prepared
    targets = len(plan.request.job.targets)
    notify(f"benching {targets} targets at {len(plan.sizes)} sizes")
    report = environment.runner_process.bench(prepared.launch, plan.request)
    references = tuple(
        analyze(summarize(report.target(approach_id)))
        for approach_id in plan.approach_ids
        if report.target(approach_id).load_error is None
    )
    user = analyze(summarize(report.target(USER_TARGET_ID))) if plan.includes_user else None
    return Measured(report, references, user)


def _subject(
    environment: Environment, request: RunBenchRequest
) -> tuple[Attempt | None, str, Language]:
    """The attempt (None for `--refs-only` without one), the slug and the language."""
    if request.references_only and request.slug is not None:
        return None, request.slug, request.language or environment.config.default_lang
    attempt = _attempt(environment, request.slug, request.language)
    language = request.language or attempt.language
    if language is None:
        raise UsageError(f"{attempt.slug} is not autograded")
    return (None if request.references_only else attempt), attempt.slug, language


def _attempt(environment: Environment, slug: str | None, language: Language | None) -> Attempt:
    """The attempt in progress, else (with a slug) the latest attempt of that problem."""
    progress = environment.progress
    try:
        return find_attempt(progress, slug, language)
    except UsageError:
        latest = (
            progress.latest_attempt(slug, language or environment.config.default_lang)
            if slug is not None
            else None
        )
        if latest is None:
            raise
        return latest


def _expected_source(meta: ProblemMeta, approach_ids: Sequence[str]) -> str | None:
    """`perf.expected_from`, else the first optimal approach, else any, in this language."""
    optimal = [a.id for a in meta.approaches if a.role is ApproachRole.OPTIMAL]
    preferred = [meta.perf.expected_from, *optimal, *approach_ids]
    return next((approach for approach in preferred if approach in approach_ids), None)


def _settings(
    environment: Environment, meta: ProblemMeta, language: Language, options: BenchOptions
) -> BenchSettings:
    config = environment.config.bench
    return BenchSettings(
        reps=options.reps or config.reps,
        warmup=WARMUPS[language],
        budget_ms=meta.perf.budget_ms,
        memory=config.memory if options.memory is None else options.memory,
        min_sample_ns=MIN_SAMPLE_NS,
    )


class _Inputs:
    """One generated input per size, the same for every target and every run."""

    def __init__(self, environment: Environment, meta: ProblemMeta) -> None:
        self._environment = environment
        self._meta = meta

    def for_sizes(self, sizes: Sequence[int], language: Language) -> tuple[BenchInput, ...]:
        files = self._environment.files
        if files.read_text(self._meta.slug, GENERATOR_FILE) is None:
            raise self._error(f"missing; cstudy bench generates its inputs with {GENERATOR_FILE}")
        generator = self._environment.content_code.generator(
            files.path(self._meta.slug, GENERATOR_FILE)
        )
        inputs: list[BenchInput] = []
        for size in sizes:
            document = generator.generate(size, bench_seed(self._meta.slug, size))
            try:
                run_input = generated_run_input(self._meta.kind, document)
            except ValueError as error:
                raise self._error(f"generate(n={size}): {error}") from None
            batch = max_batch(input_elements(document), language)
            inputs.append(BenchInput(size, run_input, batch))
        return tuple(inputs)

    def _error(self, message: str) -> ContentError:
        directory = self._environment.files.problem_directory(self._meta.slug)
        return ContentError([ContentIssue(f"{directory}/{GENERATOR_FILE}", "", message)])


class _Evaluation:
    def __init__(self, environment: Environment, plan: BenchPlan, machine: MachineState) -> None:
        self._environment = environment
        self._plan = plan
        self._machine = machine

    def evaluate(self, measured: Measured) -> BenchResult:
        plan, report = self._plan, measured.report
        warnings = [*self._machine_warnings(), *report.notes, *self._reference_load_errors(report)]
        result = BenchResult(plan, self._machine, measured=measured, warnings=tuple(warnings))
        if measured.user is None:
            return result
        user_report = report.target(USER_TARGET_ID)
        if user_report.load_error is not None:
            return replace(result, load_error=user_report.load_error)
        comparator = problem_comparator(self._environment, plan.meta)
        wrong = _WrongAnswers(plan, report, comparator).first()
        if wrong is not None:
            return replace(result, wrong_answer=wrong)
        verdict = judge(measured.user, self._ladder(measured), self._conditions())
        if verdict.time.warning is not None:
            warnings.append(verdict.time.warning)
        return replace(result, verdict=verdict, warnings=tuple(warnings))

    def _ladder(self, measured: Measured) -> Ladder:
        optimal = {a.id for a in self._plan.meta.approaches if a.role is ApproachRole.OPTIMAL}
        return Ladder(measured.references, frozenset(optimal))

    def _conditions(self) -> Conditions:
        return Conditions(bool(self._machine.warnings), MEMORY_CAPS[self._plan.language])

    def _machine_warnings(self) -> list[str]:
        return [f"{warning}: confidence capped at medium" for warning in self._machine.warnings]

    def _reference_load_errors(self, report: BenchReport) -> list[str]:
        return [
            f"reference {target.target_id} did not load: {error.type}: {error.message}"
            for target in report.targets
            if target.target_id != USER_TARGET_ID and (error := target.load_error) is not None
        ]


class _WrongAnswers:
    """The user's outputs against the expected-source reference's, size by size."""

    def __init__(self, plan: BenchPlan, report: BenchReport, comparator: Comparator) -> None:
        self._plan = plan
        self._report = report
        self._comparator = comparator

    def first(self) -> WrongAnswer | None:
        user = self._report.target(USER_TARGET_ID)
        expected = self._expected()
        for measured in user.sizes:
            if measured.failure is not None:
                return WrongAnswer(measured.size, outcome_summary(measured.failure))
            reference = expected.at(measured.size) if expected else None
            if measured.output is None or reference is None or reference.output is None:
                continue
            detail = self._mismatch(measured.size, reference.output.value, measured.output.value)
            if detail is not None:
                return WrongAnswer(measured.size, detail)
        return None

    def _expected(self) -> TargetReport | None:
        source = self._plan.expected_from
        return self._report.target(source) if source is not None else None

    def _mismatch(self, size: int, expected: JsonValue, actual: JsonValue) -> str | None:
        bench_input = next(i for i in self._plan.request.job.inputs if i.size == size)
        mismatch = self._comparator.compare(Expected(expected), actual, bench_input.input)
        if mismatch is None:
            return None
        wanted = value_text(expected, SHOWN_VALUE_LENGTH)
        got = value_text(actual, SHOWN_VALUE_LENGTH)
        reason = f" ({mismatch.detail})" if mismatch.detail else ""
        return f"expected {wanted}, got {got}{reason}"


class _Recorder:
    """Stores the run in `bench_runs` and compares it with the user's earlier runs."""

    def __init__(self, environment: Environment, plan: BenchPlan, attempt: Attempt | None) -> None:
        self._environment = environment
        self._plan = plan
        self._attempt = attempt

    def record(self, result: BenchResult) -> BenchResult:
        measured = result.measured
        if measured is None or result.load_error is not None:
            return replace(result, attempt=self._attempt)
        history = self._history(measured)
        self._environment.progress.add_bench_run(self._record(result, measured))
        return replace(result, attempt=self._attempt, history=history)

    def _history(self, measured: Measured) -> History | None:
        if measured.user is None:
            return None
        current = {
            stats.size: stats.median_ns
            for stats in measured.user.series.sizes
            if stats.median_ns is not None
        }
        past = self._environment.progress.bench_history(self._plan.meta.slug, self._plan.language)
        return compare_history(current, past)

    def _record(self, result: BenchResult, measured: Measured) -> BenchRunRecord:
        plan = self._plan
        user = measured.user
        verdict = result.verdict
        time = verdict.time if verdict else None
        user_time = user.time if user else None
        user_memory = user.memory if user else None
        series = tuple(
            summarize(target) for target in measured.report.targets if target.load_error is None
        )
        return BenchRunRecord(
            attempt_id=self._attempt.id if self._attempt and plan.includes_user else None,
            slug=plan.meta.slug,
            language=plan.language,
            ran_at=self._environment.clock.now(),
            code_hash=self._code_hash() if plan.includes_user else None,
            sizes=plan.sizes,
            series=series,
            verdict=time.verdict if time else Verdict.UNKNOWN,
            confidence=time.confidence if time else Confidence.LOW,
            user_time_band=user_time.band.value if user_time else None,
            user_memory_band=user_memory.band.value if user_memory else None,
            slope=user_time.fit.slope if user_time else None,
            r2=user_time.fit.r2 if user_time else None,
            reference_id=time.reference_id if time else None,
            ratio=time.ratio if time else None,
            environment=self._environment_record(result.machine, measured.report),
        )

    def _code_hash(self) -> str:
        watched = layout.watch_path(self._plan.meta, self._plan.language)
        return self._environment.workspace.content_hash(watched)

    def _environment_record(
        self, machine: MachineState, report: BenchReport
    ) -> dict[str, JsonValue]:
        plan = self._plan
        references = [
            solution_file(layout.reference_file_name(approach_id, plan.language))
            for approach_id in plan.approach_ids
        ]
        return {
            "cpu": machine.cpu,
            "power": machine.power.value,
            "load": machine.load_1m,
            "cores": machine.cores,
            "runner": report.runner.runner,
            "runtime": report.runner.runtime,
            "references_hash": self._environment.files.fingerprint(plan.meta.slug, references),
        }
