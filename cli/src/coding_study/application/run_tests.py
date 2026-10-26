"""`cstudy test`: run the user's code against the cases and judge it
(docs/specs/cli.md#cstudy-test).

Progressive problems run the cases of the unlocked levels (or up to `--level`); a run that passes
every unlocked level unlocks the next one and rewrites the statement to show it. Concurrent
problems run their sequential cases, then every stress case N times per variant
(docs/specs/cli.md#concurrent-problems). Other problems with `--stress N` also run N generated
inputs whose expected values are the oracle's outputs (docs/specs/cli.md#oracle-inputs).
"""

from dataclasses import dataclass, field, replace
from datetime import datetime

from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.case_materialization import CaseMaterializer, python_approaches
from coding_study.application.comparison import problem_comparator
from coding_study.application.environment import Environment
from coding_study.application.language_runs import CodeRun, LanguageRun
from coding_study.application.ports import BuildFailed, ProgressNotice, UserCode
from coding_study.application.statement_file import write_statement
from coding_study.application.stress_judging import stress_judging, without_stress
from coding_study.application.time_limits import (
    TimeLimitFlags,
    TimeLimitRequest,
    resolve_time_limits,
)
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt, RunRecord
from coding_study.domain.comparators import Comparator
from coding_study.domain.errors import UsageError
from coding_study.domain.generated_cases import OracleInput, oracle_approach, oracle_inputs
from coding_study.domain.judging import (
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
from coding_study.domain.stress_runs import PlannedRun, StressSelection, plan_runs
from coding_study.domain.stress_verdict import judge_stress
from coding_study.domain.time_limits import TimeLimits

MILLISECONDS_PER_SECOND = 1000
DEFAULT_ORACLE_SEED = 1


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


def run_tests(
    environment: Environment, request: RunTestsRequest, notify: ProgressNotice
) -> RunTestsResult:
    clock = environment.clock
    started = clock.monotonic()
    attempt = find_attempt(environment.progress, request.slug, request.language)
    language = autograded_language(attempt)
    problem = environment.problems.load(attempt.slug)
    meta = problem.meta
    oracle = _oracle_stress(environment, problem, request.stress)
    levels = _level_run(problem, attempt.level_unlocked, request.level)
    in_levels = _up_to_level(problem, levels)
    selected = _selected_cases(in_levels, request.case_ids)
    materializer = CaseMaterializer(environment, notify)
    cases = materializer.runnable_cases(without_stress(selected))
    oracle_cases = materializer.oracle_cases(meta, oracle.approach, oracle.inputs) if oracle else ()
    stress_plan = plan_runs(selected, language, request.stress)
    comparator = problem_comparator(environment, meta)
    run = LanguageRun(environment, meta, language)
    job = run.user_job((*cases, *oracle_cases), stress_plan)
    code_run = run.run(UserCode(meta, request.typecheck), [job], notify)
    judgement: Judgement | None = None
    limits: TimeLimits | None = None
    if code_run.report is not None:
        report = code_run.report.job(meta.slug)
        judgement = judge(cases, report, comparator)
        if judgement.load_error is None:
            limit_request = TimeLimitRequest(
                without_stress(problem),
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
            judging = stress_judging(environment, problem, comparator)
            judgement = with_stress(judgement, judge_stress(stress_plan, report, judging))
    result = RunTestsResult(
        meta=meta,
        attempt=attempt,
        language=language,
        cases=cases,
        comparator=comparator,
        code_run=code_run,
        judgement=judgement,
        ran_at=clock.now(),
        duration_seconds=clock.monotonic() - started,
        every_case=not request.case_ids and len(in_levels.cases) == len(problem.cases),
        time_limits=limits,
        levels=levels,
        stress_plan=stress_plan,
        oracle=oracle,
    )
    result = replace(result, attempt=_record(environment, result))
    if request.case_ids:
        return result
    return _unlock(environment, problem, result)


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
