"""`cstudy init`: create a workspace (docs/specs/installation-and-workspaces.md#cstudy-init).

A workspace is never created inside another one, nor inside a content checkout unless forced, so
solutions never land in the coding-study repository by accident. Existing files are kept.
"""

from dataclasses import dataclass
from pathlib import Path

from coding_study.application.ports import ScaffoldOutcome, WorkspaceSetup
from coding_study.domain.errors import UsageError


@dataclass(frozen=True, slots=True)
class InitRequest:
    target: Path
    git: bool = False
    """Run `git init` in the new workspace."""
    force: bool = False
    """Allow a workspace inside a content checkout."""


@dataclass(frozen=True, slots=True)
class InitializedWorkspace:
    root: Path
    files: ScaffoldOutcome


def init_workspace(setup: WorkspaceSetup, request: InitRequest) -> InitializedWorkspace:
    """Raises UsageError for a target that is or lies in a workspace, or in a checkout."""
    target = request.target
    _refuse_nested_workspace(setup, target)
    if not request.force:
        _refuse_checkout(setup, target)
    files = setup.write_missing(target)
    setup.refresh_runtime(target)
    if request.git:
        setup.init_git(target)
    return InitializedWorkspace(target, files)


def _refuse_nested_workspace(setup: WorkspaceSetup, target: Path) -> None:
    existing = setup.workspace_at_or_above(target)
    if existing is None:
        return
    if existing == target:
        raise UsageError(f"{target} is already a workspace; cstudy doctor --fix repairs it")
    raise UsageError(f"{target} is inside the workspace {existing}")


def _refuse_checkout(setup: WorkspaceSetup, target: Path) -> None:
    checkout = setup.checkout_at_or_above(target)
    if checkout is not None:
        raise UsageError(
            f"{target} is inside the coding-study checkout {checkout}, where solutions could be "
            f"committed with the content: create the workspace elsewhere, or pass --force"
        )
