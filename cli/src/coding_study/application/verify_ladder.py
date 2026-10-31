"""`cstudy verify --ladder` (D5 in docs/specs/authoring.md; performance-analysis.md#integration).

Benches the references of one language only and checks each one's measured time band against
its declared `time_class`. n and n log n share a band, so they never contradict; space is never
checked, because measured memory includes the output. A reference with too few usable sizes is
reported, not failed: it cannot contradict anything. Neither can a band that the declared class
explains within the drift tolerance; it is reported as tolerated.

Timings drift on a busy machine (an environment warning: on battery, or the load above half the
cores), so a ladder measured there is a warning, and one that contradicted its class there is
measured once more after waiting for the machine to settle; the second measurement decides.
"""

from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.ports import BuildFailed, ProgressNotice
from coding_study.application.run_bench import (
    BenchOptions,
    Measured,
    RunBenchRequest,
    measure,
    plan_bench,
)
from coding_study.domain.bench_records import MachineState
from coding_study.domain.bench_stats import size_text
from coding_study.domain.bench_verdict import LadderCheck, LadderStatus, check_ladder
from coding_study.domain.errors import ContentError
from coding_study.domain.judging import outcome_summary
from coding_study.domain.problem import Language, Problem

SETTLE_SECONDS = 60.0
"""How long a ladder that contradicted its class on a busy machine waits for the machine to
settle before it is measured again: about the time a build or a test suite takes to finish."""


@dataclass(frozen=True, slots=True)
class LadderResult:
    language: Language
    checks: tuple[LadderCheck, ...] = ()
    problems: tuple[str, ...] = ()
    """Why references could not be benched (they did not build, load or run)."""
    machine: MachineState | None = None
    """Right after the measurement that counts; None when nothing was measured."""
    retried_after: MachineState | None = None
    """The machine after a first measurement that contradicted on a busy machine."""

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

    @property
    def notes(self) -> tuple[str, ...]:
        """The busy-machine warnings: a retry first, then the conditions of the last run."""
        found: list[str] = []
        if self.retried_after is not None:
            found += [
                f"contradicted its class on a busy machine ({condition}); measured again "
                f"after waiting up to {SETTLE_SECONDS:.0f}s for it to settle"
                for condition in self.retried_after.warnings
            ]
        if self.machine is not None:
            found += [
                f"measured on a busy machine ({condition}): timings drift, "
                "so verify again when it is idle"
                for condition in self.machine.warnings
            ]
        return tuple(found)

    def contradicted_on_a_busy_machine(self) -> bool:
        busy = self.machine is not None and bool(self.machine.warnings)
        return busy and bool(self.contradictions) and not self.problems


def verify_ladder(
    environment: Environment, problem: Problem, language: Language, notify: ProgressNotice
) -> LadderResult:
    first = _measured(environment, problem, language, notify)
    if not first.contradicted_on_a_busy_machine():
        return first
    notify(
        f"ladder {language}: contradicted on a busy machine; waiting up to "
        f"{SETTLE_SECONDS:.0f}s for it to settle, then measuring again"
    )
    environment.machine.settle(SETTLE_SECONDS)
    second = _measured(environment, problem, language, notify)
    return replace(second, retried_after=first.machine)


def _measured(
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
    machine = environment.machine.snapshot()
    if isinstance(measured, BuildFailed):
        return LadderResult(language, problems=("references do not build",), machine=machine)
    return LadderResult(language, _checks(problem, measured), _problems(measured), machine)


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
