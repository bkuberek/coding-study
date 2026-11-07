"""`cstudy verify` on a service project: D1, D3, D9 and D11, each over a real stack
(docs/specs/service-projects.md#dynamic).

D1: the starter installs, comes up and answers its health path; a graded run of level 1 reports a
result for every case, which may fail; `commands.test` runs without crashing. D3: the reference
passes every case of every level. D9: its `commands.test` exits 0. D11: the install keeps its lock
file, `bootstrap` holds from empty and twice in a row, three runs of the reference give the same
verdicts, the slowest case stays within half its hang guard, the install is within a quarter of
its declared size, and nothing on `sandbox` reaches a public, LAN or metadata address.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.ports import ContainerCommand, ProgressNotice
from coding_study.application.reference_runs import ApproachResult, LanguageResult, shown
from coding_study.application.sandbox import running_stack
from coding_study.application.service_grading import ServiceGrading, grade_on_stack
from coding_study.application.service_lifecycle import (
    install_in_folder,
    prepare_engine,
    environment_of_test_command,
)
from coding_study.application.service_stacks import (
    graded_stack_plan,
    practice_stack_plan,
    service_project,
)
from coding_study.application.verify_projects import (
    STARTER_BUILDS,
    SuiteCheck,
    last_level,
    reference_build,
    reference_folder,
    starter_build,
)
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.judging import Judgement, outcome_summary, verdict_summary
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import Language, Problem
from coding_study.domain.runs import Crashed, NotRun, Returned, TimedOut, UserError
from coding_study.domain.sandbox import CommandOutcome, StackPlan, StackStartError
from coding_study.domain.service_project import INSTALLED_DIRECTORIES

D11_RUNS = 3
"""D3's run of the reference and two more."""
MAX_SLOWEST_SHARE = 0.5
SIZE_TOLERANCE = 0.25
BYTES_PER_MB = 1_000_000
NANOSECONDS_PER_MILLISECOND = 1_000_000
COMMAND_COULD_NOT_RUN = 125
"""Exits from here up say the command itself did not run: not found, not executable, killed."""
NOT_RUN = "not run: the reference does not start"
TEST_COMMAND = "commands.test"


@dataclass(frozen=True, slots=True)
class ServiceVerification:
    language: LanguageResult
    """D3 as the project's one approach; D1 as the language's problems."""
    suite: SuiteCheck
    """D9."""
    d11_problems: tuple[str, ...] = ()


def verify_service_project(
    environment: Environment, problem: Problem, language: Language, notify: ProgressNotice
) -> ServiceVerification:
    """Every check over a fresh stack of its own, one at a time, since a stack costs memory.

    Raises SandboxError when the sandbox itself fails: that says nothing about the problem.
    """
    return _ServiceChecks(environment, problem, language, notify).verify()


class _ServiceChecks:
    def __init__(
        self,
        environment: Environment,
        problem: Problem,
        language: Language,
        notify: ProgressNotice,
    ) -> None:
        self._environment = environment
        self._problem = problem
        self._language = language
        self._notify = notify
        self._service = service_project(problem)

    def verify(self) -> ServiceVerification:
        prepare_engine(self._environment, self._problem, self._notify)
        approach_id = self._problem.meta.approaches[0].id
        reference = self._reference_folder(approach_id)
        starter = list(self._starter())
        try:
            install_in_folder(self._environment, self._problem, reference, self._notify)
        except SandboxError as error:
            failed = ApproachResult(approach_id, (f"does not install: {error}",))
            result = LanguageResult(self._language, (failed,), tuple(starter))
            return ServiceVerification(result, SuiteCheck(0, 0, (NOT_RUN,)))
        first = self._graded(reference, last_level(self._problem))
        approach = ApproachResult(approach_id, _reference_failures(first))
        result = LanguageResult(self._language, (approach,), tuple(starter))
        if first.load_error is not None:
            return ServiceVerification(result, SuiteCheck(0, 0, (NOT_RUN,)))
        suite, in_stack = self._suite_and_stack_checks(reference)
        problems = (*in_stack, *self._repeated_runs(reference, first), *self._size(reference))
        return ServiceVerification(result, suite, problems)

    def _reference_folder(self, approach_id: str) -> str:
        reference_build(self._environment, self._problem, approach_id)
        return reference_folder(self._problem, approach_id)

    def _starter(self) -> Iterator[str]:
        """D1: the starter comes up, and neither its cases nor `commands.test` crash."""
        starter_build(self._environment, self._problem)
        folder = f"{STARTER_BUILDS}/{self._problem.meta.slug}"
        try:
            install_in_folder(self._environment, self._problem, folder, self._notify)
        except SandboxError as error:
            yield f"starter does not install: {error}"
            return
        judgement = self._graded(folder, FIRST_LEVEL)
        if judgement.load_error is not None:
            yield f"starter does not start: {_error_text(judgement.load_error)}"
            return
        broken = (
            verdict.outcome
            for verdict in judgement.verdicts
            if isinstance(verdict.outcome, Crashed | TimedOut | NotRun)
        )
        outcome = next(broken, None)
        if outcome is not None:
            yield f"starter {outcome_summary(outcome)}"
        yield from self._starter_test(folder)

    def _starter_test(self, folder: str) -> Iterator[str]:
        plan = practice_stack_plan(self._environment, self._problem, folder)
        try:
            with self._stack(plan):
                outcome = self._run_test(plan)
        except StackStartError as failure:
            if not failure.failure.is_your_code:
                raise
            yield f"starter's {TEST_COMMAND} has no stack: {failure}"
            return
        if outcome.timed_out or outcome.exit_code >= COMMAND_COULD_NOT_RUN:
            yield f"starter's {TEST_COMMAND} did not run: {_last_line(outcome)}"

    def _graded(self, folder: str, level: int) -> Judgement:
        plan = graded_stack_plan(self._environment, self._problem, level, folder)
        grading = ServiceGrading(self._problem, level)
        return grade_on_stack(self._environment, grading, plan, self._notify).judgement

    def _stack(self, plan: StackPlan):
        engine = self._environment.sandbox
        return running_stack(engine, plan, self._service.startup_budget, self._notify)

    def _run_test(self, plan: StackPlan) -> CommandOutcome:
        command = ContainerCommand(
            self._service.commands.test,
            environment_of_test_command(plan),
            self._service.timeouts.test,
        )
        return self._environment.sandbox.exec_app(plan, command)

    def _suite_and_stack_checks(self, reference: str) -> tuple[SuiteCheck, tuple[str, ...]]:
        """D9 in a test stack, and in the same stack D11's second `bootstrap` and its probe."""
        plan = practice_stack_plan(self._environment, self._problem, reference)
        try:
            with self._stack(plan):
                outcome = self._run_test(plan)
                problems = (*self._bootstrap_again(plan), *self._egress(plan))
        except StackStartError as failure:
            if not failure.failure.is_your_code:
                raise
            return SuiteCheck(0, 1, (f"does not run: {failure}",)), ()
        return _suite(outcome), problems

    def _bootstrap_again(self, plan: StackPlan) -> Iterator[str]:
        """A fresh stack already ran it from empty; a second run must hold on the same data."""
        command = self._service.commands.bootstrap
        if command is None:
            return
        limit = self._service.timeouts.test
        again = self._environment.sandbox.run_one_off(plan, ContainerCommand(command, {}, limit))
        if again.exit_code != 0:
            yield f"bootstrap failed when it ran twice in a row: {_last_line(again)}"

    def _egress(self, plan: StackPlan) -> Iterator[str]:
        probed = self._environment.sandbox.probe_egress(plan)
        if probed.exit_code != 0:
            yield f"a container on sandbox reached out: {_last_line(probed)}"

    def _repeated_runs(self, reference: str, first: Judgement) -> Iterator[str]:
        runs = [first]
        level = last_level(self._problem)
        runs += [self._graded(reference, level) for _ in range(D11_RUNS - 1)]
        statuses = {tuple((v.case.id, v.status) for v in run.verdicts) for run in runs}
        if len(statuses) > 1:
            yield f"the reference's verdicts differ across {D11_RUNS} runs"
        yield from self._slowest(runs)

    def _slowest(self, runs: list[Judgement]) -> Iterator[str]:
        for run in runs:
            for verdict in run.verdicts:
                guard = resolve_hang_guard_ms(
                    self._environment.config,
                    verdict.case.hang_guard_ms,
                    self._problem.meta.hang_guard_ms,
                )
                outcome = verdict.outcome
                if isinstance(outcome, Returned):
                    spent_ms = outcome.duration_ns / NANOSECONDS_PER_MILLISECOND
                    if spent_ms > guard * MAX_SLOWEST_SHARE:
                        yield (
                            f"{verdict.case.id} took {spent_ms:.0f} ms, past half "
                            f"its hang guard of {guard} ms"
                        )
                        return

    def _size(self, reference: str) -> Iterator[str]:
        """Measured, and printed for the author to copy; cstudy never writes to the content root.
        Image sizes and memory are only for showing, since they depend on the registry and on what
        else the machine holds."""
        requires = self._service.requires
        installed = INSTALLED_DIRECTORIES.get(requires.lock or "")
        declared = requires.sizes.install_mb
        if installed is None or declared is None:
            return
        measured = (
            self._environment.workspace.folder_bytes(f"{reference}/{installed}") / BYTES_PER_MB
        )
        self._notify(f"measured: requires.sizes.install_mb is about {measured:.0f}")
        if abs(measured - declared) > declared * SIZE_TOLERANCE:
            yield (
                f"requires.sizes.install_mb says {declared}, and the install takes "
                f"{measured:.0f} MB: more than a quarter away"
            )


def _reference_failures(judgement: Judgement) -> tuple[str, ...]:
    if judgement.load_error is not None:
        return (f"does not start: {_error_text(judgement.load_error)}",)
    return shown(
        [
            verdict_summary(verdict)
            for verdict in judgement.verdicts
            if verdict.status is not CaseStatus.PASS
        ]
    )


def _suite(outcome: CommandOutcome) -> SuiteCheck:
    if outcome.exit_code == 0:
        return SuiteCheck(1, 1)
    if outcome.timed_out:
        return SuiteCheck(0, 1, (f"{TEST_COMMAND} did not finish within its limit",))
    return SuiteCheck(0, 1, (f"{TEST_COMMAND} exited {outcome.exit_code}: {_last_line(outcome)}",))


def _error_text(error: UserError) -> str:
    return f"{error.type}: {error.message}"


def _last_line(outcome: CommandOutcome) -> str:
    lines = outcome.output.strip().splitlines()
    return lines[-1] if lines else f"exit {outcome.exit_code}"
