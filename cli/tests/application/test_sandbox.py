"""The sandbox as the application uses it: the engine started when needed, leftovers swept by label,
a stack always taken down, and the moment it became ready."""

from collections.abc import Iterator

import pytest

from coding_study.application.sandbox import (
    ensure_engine,
    missing_images,
    pull_images,
    running_stack,
    sweep_leftovers,
)
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    AppContainer,
    LeftoverStack,
    SandboxInventory,
    SandboxPaths,
    SandboxUser,
    StackContainer,
    StackIdentity,
    StackKind,
    StackPlan,
    StackResource,
    StackStartError,
    StartupBudget,
    StartupFailure,
)
from tests.sandbox_fakes import FakeSandbox

BUDGET = StartupBudget(up_s=300, app_ready_s=60)
PLAN = StackPlan(
    identity=StackIdentity("cstudy-t-41-abc", StackKind.TEST, "digest", "rooms", 41),
    user=SandboxUser(501, 20),
    paths=SandboxPaths("/w/projects/rooms", "/w/.cs/runs/cstudy-t-41-abc"),
    app=AppContainer("i@sha256:1", ("run",), 8000, {}),
)


def noted() -> list[str]:
    return []


def test_a_running_engine_is_left_alone():
    engine = FakeSandbox()

    ensure_engine(engine, noted().append)

    assert not engine.called("start_engine")


def test_a_stopped_engine_is_started():
    engine = FakeSandbox(engine=EngineState(EngineStatus.STOPPED))

    ensure_engine(engine, noted().append)

    assert engine.called("start_engine")


def test_an_engine_that_will_not_start_says_so():
    stopped = EngineState(EngineStatus.STOPPED)
    engine = FakeSandbox(engine=stopped, started_engine_state=stopped)

    with pytest.raises(SandboxError, match="did not start"):
        ensure_engine(engine, noted().append)


@pytest.mark.parametrize(
    ("status", "text"),
    [
        (EngineStatus.NOT_INSTALLED, "docs.docker.com"),
        (EngineStatus.NO_COMPOSE, "docs.docker.com"),
        (EngineStatus.NO_PERMISSION, "docker group"),
    ],
)
def test_an_engine_cstudy_cannot_start_gives_its_message(status, text):
    with pytest.raises(SandboxError, match=text):
        ensure_engine(FakeSandbox(engine=EngineState(status)), noted().append)


def dead_stack() -> StackContainer:
    return StackContainer("cstudy-t-41-abc", "test", "digest", 41)


def test_the_sweep_removes_a_stack_whose_owner_is_gone():
    engine = FakeSandbox(inventory_found=SandboxInventory(containers=(dead_stack(),)))

    sweep_leftovers(engine, "digest", noted().append)

    assert engine.called("remove_stack") == [
        LeftoverStack("cstudy-t-41-abc", "digest", removes_volumes=True)
    ]


def test_the_sweep_keeps_a_stack_with_a_live_owner():
    engine = FakeSandbox(
        inventory_found=SandboxInventory(containers=(dead_stack(),)), live_pids={41}
    )

    sweep_leftovers(engine, "digest", noted().append)

    assert not engine.called("remove_stack")


def test_the_sweep_removes_strays():
    stray = StackResource("n", "cstudy-t-9-abc", "test", "digest")
    volume = StackResource("v", "cstudy-t-9-abc", "test", "digest")
    engine = FakeSandbox(inventory_found=SandboxInventory(networks=(stray,), volumes=(volume,)))

    sweep_leftovers(engine, "digest", noted().append)

    assert engine.called("remove_network") == ["n"]
    assert engine.called("remove_volume") == ["v"]


def test_the_sweep_says_what_it_removed():
    lines: list[str] = []
    engine = FakeSandbox(inventory_found=SandboxInventory(containers=(dead_stack(),)))

    sweep_leftovers(engine, "digest", lines.append)

    assert lines == ["removed the leftover stack cstudy-t-41-abc"]


def test_the_sweep_is_silent_when_there_is_nothing():
    lines: list[str] = []

    sweep_leftovers(FakeSandbox(), "digest", lines.append)

    assert lines == []


def test_a_listing_that_fails_does_not_stop_the_command():
    class Refusing(FakeSandbox):
        def inventory(self) -> SandboxInventory:
            raise SandboxError("could not list")

    lines: list[str] = []

    assert not sweep_leftovers(Refusing(), "digest", lines.append)
    assert lines == ["could not list"]


def test_missing_images_are_named():
    engine = FakeSandbox(every_image_present=False, present={"a"})

    assert missing_images(engine, ("a", "b")) == ("b",)


def test_only_missing_images_are_pulled():
    engine = FakeSandbox(every_image_present=False, present={"a"})

    pull_images(engine, ("a", "b"), noted().append)

    assert engine.called("pull") == ["b"]


def steps(engine: FakeSandbox) -> list[str]:
    return [name for name, _ in engine.calls]


def test_a_stack_is_guarded_before_it_starts_and_after_it_stops():
    engine = FakeSandbox()

    with running_stack(engine, PLAN, BUDGET, noted().append):
        pass

    assert steps(engine) == ["guard", "start", "stop", "guard_released"]


def test_the_stack_passes_on_its_ready_moment():
    engine = FakeSandbox(started_at=10.0, ready_at=12.5)

    with running_stack(engine, PLAN, BUDGET, noted().append) as ready:
        assert ready.ready_at == 12.5
        assert ready.startup_seconds == 2.5


def test_a_stack_that_fails_to_start_is_still_stopped():
    failure = StackStartError(StartupFailure.SERVICE, "no")
    engine = FakeSandbox(start_error=failure)

    with pytest.raises(StackStartError), running_stack(engine, PLAN, BUDGET, noted().append):
        pass

    assert steps(engine) == ["guard", "start", "stop", "guard_released"]


def test_a_failure_in_the_block_still_stops_the_stack():
    engine = FakeSandbox()

    def run() -> Iterator[None]:
        with running_stack(engine, PLAN, BUDGET, noted().append):
            raise ValueError("boom")
        yield

    with pytest.raises(ValueError, match="boom"):
        next(run())

    assert steps(engine) == ["guard", "start", "stop", "guard_released"]


def test_a_stop_that_fails_is_said_and_does_not_hide_the_result():
    class Failing(FakeSandbox):
        def stop(self, plan: StackPlan) -> str | None:
            return "could not take it down"

    lines: list[str] = []

    with running_stack(Failing(), PLAN, BUDGET, lines.append):
        pass

    assert lines == ["could not take it down"]
