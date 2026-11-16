"""Everything a use case may touch, as ports; entrypoints build it once per command."""

from dataclasses import dataclass
from pathlib import Path

from coding_study.application.http_grading_ports import OpenStackClients
from coding_study.application.ports import (
    CalibrationCache,
    ChangeWatcher,
    Clock,
    ContentCode,
    EditorOpener,
    GeneratedCaseCache,
    GuideCatalog,
    ItemRepository,
    JdkSelector,
    LanguageServerLocator,
    MachineProbe,
    PreferencesStore,
    ProblemFiles,
    ProblemRepository,
    ProblemSetStore,
    ProgressStore,
    RunnerProcess,
    SandboxEngine,
    StudyGuides,
    ToolchainCheck,
    Toolchains,
    UserDocs,
    Workspace,
)
from coding_study.domain.config import Config


@dataclass(frozen=True, slots=True)
class ProblemDestination:
    """Where `cstudy new` writes: an editable content checkout, or the workspace's own problems/
    (docs/specs/installation-and-workspaces.md#your-own-problems)."""

    files: ProblemFiles
    """The problems already in this destination, and the directory the new one goes to."""
    writer: Workspace
    """Writes paths relative to the destination root, e.g. `problems/max-gap/meta.yaml`."""


@dataclass(frozen=True, slots=True)
class Environment:
    root: Path
    """The absolute workspace root: practice projects, `.cs/` and progress.db live under it."""
    content_root: Path
    """The absolute content root: problems/, runners/ and schemas/."""
    config: Config
    problems: ProblemRepository
    files: ProblemFiles
    """The same problems as `problems`: the catalog with the workspace's own overlaid."""
    progress: ProgressStore
    toolchains: Toolchains
    jdk: JdkSelector
    """The JDK that Java and Kotlin build and run with: the one the shell selects."""
    toolchain_check: ToolchainCheck
    """Whether the other languages' programs (`node`, `go`, `cargo`, the workspace's Python) are
    there; `cstudy verify` skips a language without its program."""
    runner_process: RunnerProcess
    workspace: Workspace
    content_code: ContentCode
    case_cache: GeneratedCaseCache
    calibrations: CalibrationCache
    clock: Clock
    editor: EditorOpener
    watcher: ChangeWatcher
    items: ItemRepository
    """The rubric-checked problems of problems/."""
    guides: GuideCatalog
    """Concept guides and learning paths in guides/ (docs/specs/guides.md)."""
    docs: UserDocs
    """The user docs in user-docs/ (docs/specs/user-docs.md)."""
    machine: MachineProbe
    new_problems: ProblemDestination
    study_guides: StudyGuides
    language_servers: LanguageServerLocator
    """The code-intelligence servers in the workspace's `.cs/lsp/`."""
    sandbox: SandboxEngine
    """The container engine of service projects; nothing else ever reaches it."""
    stack_clients: OpenStackClients
    """Opens the HTTP clients of a ready stack, for the grader and for `cstudy dev`."""
    problem_sets: ProblemSetStore
    """The workspace's `sets.yaml`."""
    preferences: PreferencesStore
    """The web UI's preferences: a service project's install builds the server its sidecar runs,
    if that server is not the one of `.cs/lsp/`, only while `code_intelligence` is on."""
