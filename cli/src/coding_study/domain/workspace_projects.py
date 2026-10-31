"""Project folders in the workspace (docs/specs/installation-and-workspaces.md#project-folders).

`cstudy start` fills `projects/<slug>/` from a project problem's starter and links it to the
workspace's toolchain: a Python folder through its `.venv` link, a Go folder through a `go.work` of
its own. What tools write into a folder is untracked, as the workspace's `.gitignore` has it: the
`.venv` link, `node_modules`, caches, Gradle's build output, a `uv.lock`, and Go's `go.work` and
`go.work.sum`. `cstudy test --watch` ignores those, `code_hash` leaves them out, and an archived
attempt goes without them. Paths are POSIX strings, relative to the workspace root or, where a name
says so, to the folder.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from coding_study.domain import layout
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta
from coding_study.domain.project import PATH_SEPARATOR

PROJECTS_DIRECTORY = "projects"
PYTEST_INSTALL_COMMAND = f"uv add --dev pytest --directory {layout.PYTHON_PROJECT}"
"""A Python project's tests run in the workspace venv; workspaces created before the template
listed pytest lack it."""
UNTRACKED_DIRECTORIES = frozenset(
    {
        *(layout.PYTHON_VENV, "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"),
        *("build", ".gradle", ".kotlin"),
        "target",
    }
)
"""Untracked wherever they appear in a folder: `build`, `.gradle` and `.kotlin` are what a Gradle
build writes, `target` what the native `cargo test` builds."""
GO_MODULE_FILE = "go.mod"
GO_WORK_FILE = "go.work"
GO_WORK_SUM_FILE = "go.work.sum"
GO_WORK_VERSION = "1.24"
"""The `go` line of a folder's `go.work`, and the one a Go starter's `go.mod` declares."""
UNTRACKED_ROOT_FILES = frozenset({"uv.lock", GO_WORK_FILE, GO_WORK_SUM_FILE, "Cargo.lock"})
"""Untracked at the root of a folder only: a plain `uv run` there writes a `uv.lock`,
`cstudy start` a Go folder's `go.work`, and the native `cargo test` a `Cargo.lock`."""
GO_VENDORED_MODULES: Mapping[str, str] = {"github.com/shopspring/decimal": "v1.5.0"}
"""The modules a Go solution may import beyond the standard library, at their vendored versions:
copies in the runner runtime, reached through `replace`, so nothing is downloaded
(docs/specs/runners.md#go-build-details)."""
_FOLDER_TO_WORKSPACE_ROOT = "../.."
"""From `projects/<slug>/` up to the workspace root."""
_GO_THIRD_PARTY = ".cs/runtime/runners/go/third_party"
"""The vendored Go modules' copies, relative to the workspace root."""
_GO_COMMENT = re.compile(r"//.*")
_GO_BLOCK_END = ")"
_GO_REPLACEMENT_ARROW = "=>"
CARGO_MANIFEST = "Cargo.toml"
"""A project folder holding one is a Rust project."""
CARGO_CONFIG_FILE = ".cargo/config.toml"
RUST_VENDOR_DIRECTORY = ".cs/runtime/runners/rust/vendor"
"""The runtime's vendored crates, relative to the workspace root."""
RUST_VENDORED_SOURCE = "cstudy-vendor"
"""The name of the source that replaces crates.io, in a folder's config as in every build."""
RUST_CARGO_CONFIG = f"""\
[source.crates-io]
replace-with = "{RUST_VENDORED_SOURCE}"

[source.{RUST_VENDORED_SOURCE}]
directory = "{_FOLDER_TO_WORKSPACE_ROOT}/{RUST_VENDOR_DIRECTORY}"
"""
"""A Rust folder's `.cargo/config.toml`: crates.io from the vendored crates, by a path relative
to the folder, so rust-analyzer and the native `cargo test` build offline."""


@dataclass(frozen=True, slots=True)
class ToolchainLink:
    """A symbolic link that reaches the workspace's toolchain from a project folder."""

    path: str
    """Relative to the folder."""
    target: str
    """Relative to the folder, so the link survives moving and cloning the workspace."""


@dataclass(frozen=True, slots=True)
class ToolchainFile:
    """A file that reaches the workspace's toolchain from a project folder, written when missing."""

    path: str
    """Relative to the folder."""
    text: str


@dataclass(frozen=True, slots=True)
class GoModuleFile:
    """What a `go.mod` declares; None for a directive it lacks."""

    module: str | None
    go: str | None
    requires: Mapping[str, str] = field(default_factory=dict[str, str])
    """The version of each required module."""
    replaces: Mapping[str, str] = field(default_factory=dict[str, str])
    """What replaces each module: a path, or a module and version."""


@dataclass(frozen=True, slots=True)
class GoProjectFolder:
    """What `cstudy doctor` finds in a Go project folder (a folder with a `go.mod`)."""

    folder: str
    """`projects/<slug>`, relative to the workspace root."""
    module: str | None
    """Its `go.mod`'s module path."""
    has_work_file: bool
    unresolved: tuple[str, ...] = ()
    """The local `replace` targets of its `go.mod` that name no directory."""


def project_folder(slug: str) -> str:
    return f"{PROJECTS_DIRECTORY}{PATH_SEPARATOR}{slug}"


def folder_language(meta: ProblemMeta) -> Language | None:
    """The language of a project problem's folder, the one its problem lists (check S14); None
    for a problem of another kind, which has no folder."""
    return meta.languages[0] if meta.kind is ProblemKind.PROJECT else None


def toolchain_link(language: Language) -> ToolchainLink | None:
    """Python folders link `.venv` to the workspace venv; the others reach their toolchain through
    their build files and need no link."""
    if language is Language.PYTHON:
        venv = PATH_SEPARATOR.join(
            (_FOLDER_TO_WORKSPACE_ROOT, layout.PYTHON_PROJECT, layout.PYTHON_VENV)
        )
        return ToolchainLink(layout.PYTHON_VENV, venv)
    return None


def toolchain_files(language: Language) -> tuple[ToolchainFile, ...]:
    """A Go folder holds a `go.work` of its own, so the workspace's root `go.work` never claims
    it; a Rust folder reaches the vendored crates through `.cargo/config.toml`; the others need
    none."""
    if language is Language.GO:
        return (ToolchainFile(GO_WORK_FILE, f"go {GO_WORK_VERSION}\n\nuse .\n"),)
    if language is Language.RUST:
        return (ToolchainFile(CARGO_CONFIG_FILE, RUST_CARGO_CONFIG),)
    return ()


def go_vendored_replacement(module: str) -> str:
    """The `replace` target of a vendored module in a Go folder's `go.mod`: its copy in the
    runner runtime, relative to `projects/<slug>/`."""
    return PATH_SEPARATOR.join((_FOLDER_TO_WORKSPACE_ROOT, _GO_THIRD_PARTY, module))


def go_module_file(text: str) -> GoModuleFile:
    """The directives of a `go.mod`, single or in blocks, without comments."""
    module = go = None
    requires: dict[str, str] = {}
    replaces: dict[str, str] = {}
    block: str | None = None
    for raw in text.splitlines():
        words = _GO_COMMENT.sub("", raw).split()
        if not words:
            continue
        if block is not None:
            if words == [_GO_BLOCK_END]:
                block = None
            else:
                _directive(block, words, requires, replaces)
            continue
        verb, *rest = words
        if rest == ["("]:
            block = verb
        elif verb == "module" and rest:
            module = rest[0].strip('"')
        elif verb == "go" and rest:
            go = rest[0]
        else:
            _directive(verb, rest, requires, replaces)
    return GoModuleFile(module, go, requires, replaces)


def _directive(
    verb: str, words: list[str], requires: dict[str, str], replaces: dict[str, str]
) -> None:
    if verb == "require" and len(words) >= 2:
        requires[words[0]] = words[1]
    elif verb == "replace" and _GO_REPLACEMENT_ARROW in words:
        arrow = words.index(_GO_REPLACEMENT_ARROW)
        replaces[words[0]] = " ".join(words[arrow + 1 :])


def go_folder_problems(folders: Iterable[GoProjectFolder]) -> tuple[str, ...]:
    """What `cstudy doctor` warns about in the Go project folders, in folder order: a missing
    `go.work`, a `replace` that names no directory, and a module path two folders declare."""
    ordered = sorted(folders, key=lambda found: found.folder)
    problems: list[str] = []
    for found in ordered:
        if not found.has_work_file:
            problems.append(f"{found.folder} has no {GO_WORK_FILE}")
        problems += (
            f"{found.folder}/{GO_MODULE_FILE} replaces a module with {target}, which does not exist"
            for target in found.unresolved
        )
    by_module: dict[str, list[str]] = {}
    for found in ordered:
        if found.module is not None:
            by_module.setdefault(found.module, []).append(found.folder)
    problems += (
        _sharing(sharing, module) for module, sharing in by_module.items() if len(sharing) > 1
    )
    return tuple(problems)


def _sharing(folders: Sequence[str], module: str) -> str:
    *others, last = folders
    each = "both" if len(folders) == 2 else "all"
    return f"{', '.join(others)} and {last} {each} declare module {module}"


def is_untracked(path: str) -> bool:
    """Whether `path`, relative to a project folder, is something a tool wrote."""
    return path in UNTRACKED_ROOT_FILES or _names_untracked(path.split(PATH_SEPARATOR))


def project_slug(path: str) -> str | None:
    """The folder, which is the problem's slug, that the file `path` lies in; None for a path
    outside every project folder or under one's `.venv`, `node_modules` or caches
    (docs/specs/cli.md#solution-file-targets)."""
    match path.split(PATH_SEPARATOR):
        case [directory, slug, *directories, _file] if directory == PROJECTS_DIRECTORY and slug:
            return None if _names_untracked(directories) else slug
        case _:
            return None


def _names_untracked(segments: Sequence[str]) -> bool:
    return any(segment in UNTRACKED_DIRECTORIES for segment in segments)
