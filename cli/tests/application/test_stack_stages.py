"""The stages of a service project's stack, which its progress notices name
(docs/specs/cli.md#event-stream): a terminal prints each as text, and `--events` adds the stage."""

import pytest

from coding_study.application.sandbox import ensure_engine, pull_images, reported_stack
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    AppContainer,
    SandboxPaths,
    SandboxUser,
    StackIdentity,
    StackKind,
    StackPlan,
    StackStartError,
    StartupBudget,
    StartupFailure,
)
from coding_study.domain.stack_progress import StackNotice, StackStage, stage_of
from tests.sandbox_fakes import FakeSandbox

BUDGET = StartupBudget(up_s=300, app_ready_s=60)
PLAN = StackPlan(
    identity=StackIdentity("cstudy-t-41-abc", StackKind.TEST, "digest", "rooms", 41),
    user=SandboxUser(501, 20),
    paths=SandboxPaths("/w/projects/rooms", "/w/.cs/runs/cstudy-t-41-abc"),
    app=AppContainer("i@sha256:1", ("run",), 8000, {}),
)


def stages(notices: list[str]) -> list[StackStage | None]:
    return [stage_of(notice) for notice in notices]


def test_a_stack_notice_prints_as_its_text():
    notice = StackNotice("starting the stack", StackStage.STARTING)

    assert f"{notice}" == "starting the stack"


def test_a_stack_notice_names_its_stage():
    assert stage_of(StackNotice("pulling node", StackStage.PULLING)) is StackStage.PULLING


def test_a_plain_notice_names_no_stage():
    assert stage_of("removed the leftover stack") is None


def test_starting_a_stopped_engine_is_the_docker_stage():
    notices: list[str] = []
    engine = FakeSandbox(engine=EngineState(EngineStatus.STOPPED))

    ensure_engine(engine, notices.append)

    assert stages(notices) == [StackStage.DOCKER]


def test_a_pull_is_the_pulling_stage():
    notices: list[str] = []

    pull_images(FakeSandbox(every_image_present=False), ["node:24"], notices.append)

    assert set(stages(notices)) == {StackStage.PULLING}


def test_a_reported_stack_says_it_starts_is_ready_and_is_down():
    notices: list[str] = []

    with reported_stack(FakeSandbox(), PLAN, BUDGET, notices.append):
        pass

    assert stages(notices) == [StackStage.STARTING, StackStage.READY, StackStage.STOPPED]


def test_ready_carries_the_startup_which_nothing_counts():
    notices: list[str] = []

    with reported_stack(FakeSandbox(started_at=10.0, ready_at=12.5), PLAN, BUDGET, notices.append):
        pass

    ready = notices[1]
    assert isinstance(ready, StackNotice)
    assert ready.startup_s == 2.5


def test_a_stack_that_did_not_become_ready_failed_and_is_down():
    notices: list[str] = []
    engine = FakeSandbox(start_error=StackStartError(StartupFailure.APP_EXITED, "exited"))

    with pytest.raises(StackStartError), reported_stack(engine, PLAN, BUDGET, notices.append):
        pass

    assert stages(notices) == [StackStage.STARTING, StackStage.FAILED, StackStage.STOPPED]


def test_a_sandbox_error_once_ready_is_no_failed_start():
    notices: list[str] = []

    with pytest.raises(SandboxError), reported_stack(FakeSandbox(), PLAN, BUDGET, notices.append):
        raise SandboxError("the exec failed")

    assert StackStage.FAILED not in stages(notices)


def test_a_stack_interrupted_while_ready_is_still_down():
    notices: list[str] = []

    with (
        pytest.raises(KeyboardInterrupt),
        reported_stack(FakeSandbox(), PLAN, BUDGET, notices.append),
    ):
        raise KeyboardInterrupt

    assert stages(notices)[-1] is StackStage.STOPPED
