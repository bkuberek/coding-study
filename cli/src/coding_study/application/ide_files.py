"""`cstudy ide`, and the IDE step of `cstudy init`: write the IDE project files of a workspace
(docs/specs/installation-and-workspaces.md#ide-files).

Which files may be rewritten is the domain's rule (`coding_study.domain.ide`); this use case reads
what is on disk, applies the plan and records what it wrote.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from coding_study.domain.ide import (
    Change,
    GeneratedFile,
    Ide,
    Regeneration,
    Step,
    plan_regeneration,
)


class IdeRenderer(Protocol):
    """One IDE's project files."""

    def files(self) -> tuple[GeneratedFile, ...]: ...


class GeneratedFiles(Protocol):
    """The workspace's files, by workspace-relative path, and the manifest of those cstudy
    wrote."""

    def digest(self, path: str) -> str | None:
        """The SHA-256 of the file at `path`, or None when there is none."""
        ...

    def write(self, path: str, content: str) -> None: ...

    def remove(self, path: str) -> None: ...

    def manifest(self) -> dict[str, str]:
        """The digest recorded for each file cstudy wrote, by path."""
        ...

    def save_manifest(self, manifest: Mapping[str, str]) -> None: ...


@dataclass(frozen=True, slots=True)
class IdeRequest:
    ides: tuple[Ide, ...]
    force: bool = False
    """Overwrite files edited since cstudy wrote them, and files it never wrote."""


@dataclass(frozen=True, slots=True)
class IdeReport:
    ides: tuple[Ide, ...]
    steps: tuple[Step, ...]

    @property
    def changed(self) -> bool:
        return any(step.change is not Change.UNCHANGED for step in self.steps)

    def paths(self, change: Change) -> tuple[str, ...]:
        return tuple(step.path for step in self.steps if step.change is change)


def generate_ide_files(
    renderers: Mapping[Ide, IdeRenderer], files: GeneratedFiles, request: IdeRequest
) -> IdeReport:
    generated = tuple(file for ide in request.ides for file in renderers[ide].files())
    recorded = files.manifest()
    regeneration = Regeneration(generated, recorded, request.ides, force=request.force)
    current = {path: files.digest(path) for path in regeneration.paths()}
    plan = plan_regeneration(regeneration, current)
    for step in plan.steps:
        _apply(step, files)
    if plan.manifest != recorded:
        files.save_manifest(plan.manifest)
    return IdeReport(request.ides, plan.steps)


def _apply(step: Step, files: GeneratedFiles) -> None:
    if step.content is not None:
        files.write(step.path, step.content)
    elif step.change is Change.REMOVED:
        files.remove(step.path)
