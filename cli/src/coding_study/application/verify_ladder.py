"""`cstudy verify --ladder` (D5 in docs/specs/authoring.md; performance-analysis.md#integration).

Benches the references of one language only and checks each one's measured time band against
its declared `time_class`. n and n log n share a band, so they never contradict; space is never
checked, because measured memory includes the output. A reference with too few usable sizes is
reported, not failed: it cannot contradict anything. Neither can a band that the declared class
explains within the drift tolerance; it is reported as tolerated.
"""

from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.ports import BuildFailed, ProgressNotice
from coding_study.application.run_bench import (
    BenchOptions,
    Measured,
    RunBenchRequest,
    measure,
    plan_bench,
)
from coding_study.domain.bench_stats import size_text
from coding_study.domain.bench_verdict import LadderCheck, LadderStatus, check_ladder
from coding_study.domain.errors import ContentError
from coding_study.domain.judging import outcome_summary
from coding_study.domain.problem import Language, Problem


@dataclass(frozen=True, slots=True)
class LadderResult:
    language: Language
    checks: tuple[LadderCheck, ...] = ()
    problems: tuple[str, ...] = ()
    """Why references could not be benched (they did not build, load or run)."""

    @property
    def contradictions(self) -> tuple[LadderCheck, ...]:
        return tuple(c for c in self.checks if c.status is LadderStatus.CONTRADICTS)

    @property
    def unclassified(self) -> tuple[LadderCheck, ...]:
        return tuple(c for c in self.checks if c.status is LadderStatus.UNCLASSIFIED)

    @property
    def tolerated(self) -> tuple[LadderCheck, ...]:
        return tuple(c for c in self.checks if c.status is LadderStatus.TOLERATED)

    @property
    def passed(self) -> bool:
        return not self.problems and not self.contradictions


def verify_ladder(
    environment: Environment, problem: Problem, language: Language, notify: ProgressNotice
) -> LadderResult:
    request = RunBenchRequest(
        problem.meta.slug, language, BenchOptions(memory=False), references_only=True
    )
    try:
        plan = plan_bench(environment, problem, language, request)
        if not plan.approach_ids:
            return LadderResult(language)
        measured = measure(environment, plan, notify)
    except ContentError as error:
        return LadderResult(language, problems=tuple(str(issue) for issue in error.issues))
    if isinstance(measured, BuildFailed):
        return LadderResult(language, problems=("references do not build",))
    return LadderResult(language, _checks(problem, measured), _problems(measured))


def _checks(problem: Problem, measured: Measured) -> tuple[LadderCheck, ...]:
    approaches = {approach.id: approach for approach in problem.meta.approaches}
    return tuple(
        check_ladder(approaches[analysis.target_id], analysis) for analysis in measured.references
    )


def _problems(measured: Measured) -> tuple[str, ...]:
    found: list[str] = []
    for target in measured.report.targets:
        if target.load_error is not None:
            error = target.load_error
            found.append(f"{target.target_id} does not load: {error.type}: {error.message}")
        for size in target.sizes:
            if size.failure is not None:
                summary = outcome_summary(size.failure)
                found.append(f"{target.target_id} failed at n={size_text(size.size)}: {summary}")
    return tuple(found)
