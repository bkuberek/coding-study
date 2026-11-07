"""A running stack, as the HTTP grader sees it (`GradedStack` in `http_grading_ports.py`).

Every restart here spends the first clock: it comes between two cases and counts toward neither. A
failure says what happened and the grader carries it into the case's verdict.
"""

from dataclasses import dataclass

from coding_study.application.http_grading_ports import AppExit, StackEndpoints, StackStepError
from coding_study.application.ports import ContainerCommand, SandboxEngine
from coding_study.domain.sandbox import (
    RESET_PHASE_APPLY,
    RESET_PHASE_VARIABLE,
    ReadyStack,
    StackPlan,
    StackStartError,
)
from coding_study.domain.service_project import ServiceProject


@dataclass(frozen=True, slots=True)
class RunningStack:
    plan: StackPlan
    ready: ReadyStack


class SandboxGradedStack:
    def __init__(self, engine: SandboxEngine, stack: RunningStack, service: ServiceProject) -> None:
        self._engine = engine
        self._plan = stack.plan
        self._ready = stack.ready
        self._service = service

    @property
    def endpoints(self) -> StackEndpoints:
        mocks = self._plan.mocks
        return StackEndpoints(
            app_url=self._ready.app_url,
            control_url=self._ready.control_url,
            control_token=mocks.control_token if mocks is not None else "",
            mocks=mocks.aliases if mocks is not None else (),
        )

    def restart_app(self) -> None:
        try:
            self._engine.restart_app(self._plan, self._ready, self._service.startup_budget)
        except StackStartError as failed:
            raise StackStepError(str(failed), failed.output) from failed

    def restart_app_with_fresh_data(self) -> None:
        """Without `commands.reset`, a fresh start only restarts the app."""
        reset = self._service.commands.reset
        if reset is None:
            self.restart_app()
            return
        try:
            self._engine.stop_app(self._plan)
            self._reset(reset)
            self._engine.start_app(self._plan, self._ready, self._service.startup_budget)
        except StackStartError as failed:
            raise StackStepError(str(failed), failed.output) from failed

    def _reset(self, reset: tuple[str, ...]) -> None:
        limit = self._service.timeouts.reset
        command = ContainerCommand(reset, {RESET_PHASE_VARIABLE: RESET_PHASE_APPLY}, limit)
        outcome = self._engine.run_one_off(self._plan, command)
        if outcome.timed_out:
            raise StackStepError(f"commands.reset did not finish within {limit} s", outcome.output)
        if outcome.exit_code != 0:
            raise StackStepError(f"commands.reset exited with {outcome.exit_code}", outcome.output)

    def app_exit(self, within_ms: int) -> AppExit | None:
        ended = self._engine.app_exit(self._plan, within_ms)
        return None if ended is None else AppExit(ended.exit_code, ended.output)
