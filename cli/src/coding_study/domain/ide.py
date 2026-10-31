"""IDE project files cstudy generates in a workspace, and when it may rewrite them
(docs/specs/installation-and-workspaces.md#ide-files).

The files are the user's to edit. cstudy records the digest of each file it writes and, when it
generates them again, overwrites only files that are missing or still as it wrote them; an edited
file, or one cstudy never wrote, is kept unless forced. A file cstudy no longer generates is
removed while it is unchanged, and forgotten once edited. Files of an IDE that is not being
generated are left alone.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class Ide(StrEnum):
    VSCODE = "vscode"
    IDEA = "idea"

    @property
    def directory(self) -> str:
        """Where its project files live, relative to the workspace root."""
        return IDE_DIRECTORIES[self]


IDE_DIRECTORIES: Mapping[Ide, str] = {Ide.VSCODE: ".vscode", Ide.IDEA: ".idea"}
VSCODE_SETTINGS = f"{IDE_DIRECTORIES[Ide.VSCODE]}/settings.json"
"""VS Code's settings, relative to the workspace root."""


class Change(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    KEPT = "kept"
    """Left as it is: edited since cstudy wrote it, or never written by cstudy."""
    REMOVED = "removed"


def content_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True, slots=True)
class IdeWorkspace:
    """What the generated files depend on in the workspace itself."""

    rust_projects: tuple[str, ...] = ()
    """The manifest of each Rust project folder, `projects/<slug>/Cargo.toml`, in path order:
    rust-analyzer analyses only the Cargo projects `linkedProjects` names."""


NO_PROJECT_FOLDERS = IdeWorkspace()
"""A workspace without project folders, as a new one is."""


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    path: str
    """Relative to the workspace root, with `/` separators."""
    content: str

    @property
    def digest(self) -> str:
        return content_digest(self.content.encode())


@dataclass(frozen=True, slots=True)
class Step:
    path: str
    change: Change
    content: str | None = None
    """What to write, for a created or updated file."""


@dataclass(frozen=True, slots=True)
class Plan:
    steps: tuple[Step, ...]
    manifest: dict[str, str]
    """The digests to record afterwards, by path."""


@dataclass(frozen=True, slots=True)
class Regeneration:
    generated: tuple[GeneratedFile, ...]
    recorded: Mapping[str, str]
    """The digests recorded when cstudy last wrote its files, by path."""
    ides: tuple[Ide, ...]
    force: bool = False
    """Overwrite kept files too."""

    def owns(self, path: str) -> bool:
        return any(path.startswith(f"{ide.directory}/") for ide in self.ides)

    def paths(self) -> set[str]:
        """The files whose current digest the plan needs."""
        recorded = {path for path in self.recorded if self.owns(path)}
        return {file.path for file in self.generated} | recorded


def plan_regeneration(regeneration: Regeneration, current: Mapping[str, str | None]) -> Plan:
    """`current` maps each of `regeneration.paths()` to the digest of the file there, or None
    when there is none."""
    generated_paths = {file.path for file in regeneration.generated}
    manifest = {
        path: digest
        for path, digest in regeneration.recorded.items()
        if not regeneration.owns(path)
    }
    steps: list[Step] = []
    for file in regeneration.generated:
        step = _generated_step(regeneration, file, current.get(file.path))
        steps.append(step)
        if step.change is not Change.KEPT:
            manifest[file.path] = file.digest
        elif file.path in regeneration.recorded:
            manifest[file.path] = regeneration.recorded[file.path]
    for path, digest in regeneration.recorded.items():
        if regeneration.owns(path) and path not in generated_paths:
            steps.extend(_stale_step(path, digest, current.get(path)))
    return Plan(tuple(steps), manifest)


def _generated_step(regeneration: Regeneration, file: GeneratedFile, current: str | None) -> Step:
    if current is None:
        return Step(file.path, Change.CREATED, file.content)
    if current == file.digest:
        return Step(file.path, Change.UNCHANGED)
    if regeneration.force or current == regeneration.recorded.get(file.path):
        return Step(file.path, Change.UPDATED, file.content)
    return Step(file.path, Change.KEPT)


def _stale_step(path: str, recorded: str, current: str | None) -> tuple[Step, ...]:
    """A file cstudy no longer generates: gone already, removed, or the user's from now on."""
    if current is None:
        return ()
    return (Step(path, Change.REMOVED if current == recorded else Change.KEPT),)
