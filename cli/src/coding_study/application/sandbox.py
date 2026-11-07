"""The sandbox of a service project, as a use case needs it: the engine started when it is needed,
leftovers swept by label, images pulled with progress, and a stack that always comes down
(docs/specs/service-projects.md#lifecycle).

A bank problem never reaches this module, so it never asks Docker anything.
"""

from collections.abc import Generator, Sequence
from contextlib import contextmanager

from coding_study.application.ports import ProgressNotice, SandboxEngine
from coding_study.domain.docker_engine import EngineStatus, engine_problem
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    Leftovers,
    ReadyStack,
    StackPlan,
    StartupBudget,
    leftovers_in,
)


def ensure_engine(engine: SandboxEngine, notify: ProgressNotice) -> None:
    """Starts a stopped engine. Raises SandboxError with the state's message when it does not
    answer, is missing or refuses you: nothing has been written by then."""
    state = engine.state()
    if state.status is EngineStatus.STOPPED:
        engine.start_engine(notify)
        state = engine.state()
    problem = engine_problem(state, engine.platform())
    if problem is not None:
        raise SandboxError(problem)


def current_leftovers(engine: SandboxEngine, workspace: str | None) -> Leftovers:
    """What a sweep would remove; raises SandboxError when the engine cannot list it."""
    return leftovers_in(engine.inventory(), engine.is_alive, workspace)


def sweep_leftovers(
    engine: SandboxEngine, workspace: str | None, notify: ProgressNotice
) -> Leftovers:
    """Removes what carries `cstudy`'s labels and has no owner left, and nothing else: of one
    workspace, or of every one when `workspace` is None. A failure to list is said, not raised,
    since a leftover must not stop the command that found it."""
    try:
        found = current_leftovers(engine, workspace)
    except SandboxError as error:
        notify(str(error))
        return Leftovers()
    for stack in found.stacks:
        _said(engine.remove_stack(stack), f"the leftover stack {stack.name}", notify)
    for network in found.networks:
        _said(engine.remove_network(network), f"the leftover network {network}", notify)
    for volume in found.volumes:
        _said(engine.remove_volume(volume), f"the leftover volume {volume}", notify)
    return found


def _said(removed: bool, what: str, notify: ProgressNotice) -> None:
    notify(f"removed {what}" if removed else f"could not remove {what}")


def missing_images(engine: SandboxEngine, images: Sequence[str]) -> tuple[str, ...]:
    return tuple(image for image in images if not engine.image_present(image))


def pull_images(engine: SandboxEngine, images: Sequence[str], notify: ProgressNotice) -> None:
    """Pulls those not here yet; raises SandboxError when one cannot be pulled."""
    for image in missing_images(engine, images):
        notify(f"pulling {image}")
        engine.pull(image, notify)


@contextmanager
def running_stack(
    engine: SandboxEngine, plan: StackPlan, budget: StartupBudget, notify: ProgressNotice
) -> Generator[ReadyStack]:
    """A stack that is ready for the block and gone after it, however the block or the start ends.
    The guard is there first and goes last, so a `cstudy` that dies at any point leaves nothing."""
    with engine.guard(plan.identity):
        try:
            yield engine.start(plan, budget)
        finally:
            problem = engine.stop(plan)
            if problem is not None:
                notify(problem)
