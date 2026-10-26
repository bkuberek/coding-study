"""Where the content and the workspace are (docs/specs/installation-and-workspaces.md).

Content: `CSTUDY_CONTENT`, then the copy bundled in the installed package, then the source checkout
the package runs from. Workspace: `CSTUDY_WORKSPACE`, then the nearest directory upward holding the
marker, then the current directory. The global `--content` and `--workspace` flags reach here as
these variables.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from coding_study.adapters.workspace_marker import (
    MARKER_FILE,
    SCHEMA_VERSION,
    MarkerError,
    has_marker,
    read_marker,
)

CONTENT_VARIABLE = "CSTUDY_CONTENT"
WORKSPACE_VARIABLE = "CSTUDY_WORKSPACE"
CONTENT_MARKERS = ("problems", "schemas")
BUNDLED_CONTENT = "content"
"""The directory, inside the installed `coding_study` package, that the wheel bundles."""
PACKAGE_DIRECTORY = Path(__file__).resolve().parents[1]
CHECKOUT_DEPTH = 2
"""A checkout holds the package at `cli/src/coding_study`, two levels below its root."""
CACHE_VARIABLE = "XDG_CACHE_HOME"
DEFAULT_CACHE_DIRECTORY = ".cache"
APPLICATION_DIRECTORY = "coding-study"
CATALOG_CACHE = "catalog"


class ContentRootError(LookupError):
    pass


class WorkspaceError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class ContentRoot:
    path: Path
    editable: bool
    """A checkout `cstudy new` writes into; the bundled copy is read-only."""


def find_content_root(environ: Mapping[str, str], package: Path | None = None) -> ContentRoot:
    """`package` is the `coding_study` package directory; default: the one running."""
    override = environ.get(CONTENT_VARIABLE, "")
    if override:
        return ContentRoot(_explicit_content(Path(override)), editable=True)
    package = package or PACKAGE_DIRECTORY
    bundled = package / BUNDLED_CONTENT
    if is_content_root(bundled):
        return ContentRoot(bundled, editable=False)
    checkout = package.parents[CHECKOUT_DEPTH]
    if is_content_root(checkout):
        return ContentRoot(checkout, editable=True)
    raise ContentRootError(
        f"no content bundled in {package} and no checkout at {checkout}: set {CONTENT_VARIABLE}"
    )


def is_content_root(directory: Path) -> bool:
    return all((directory / marker).is_dir() for marker in CONTENT_MARKERS)


def enclosing_content_checkout(directory: Path) -> Path | None:
    """The nearest content root at or above `directory`; a workspace has no schemas/."""
    return next((found for found in _upward(directory) if is_content_root(found)), None)


def enclosing_workspace(directory: Path) -> Path | None:
    """The nearest directory at or above `directory` that holds the workspace marker."""
    return next((found for found in _upward(directory) if has_marker(found)), None)


def workspace_directory(cwd: Path, environ: Mapping[str, str]) -> Path:
    """Where the workspace is, or would be: it may hold no marker yet."""
    override = environ.get(WORKSPACE_VARIABLE, "")
    if override:
        return (cwd / Path(override).expanduser()).resolve()
    return enclosing_workspace(cwd) or cwd


def find_workspace(cwd: Path, environ: Mapping[str, str]) -> Path:
    """The workspace root; raises WorkspaceError without a marker or for a newer schema."""
    directory = workspace_directory(cwd, environ)
    if not has_marker(directory):
        raise WorkspaceError(
            f"no coding-study workspace at {directory} (no {MARKER_FILE}): "
            f"run cstudy init to create one, or pass --workspace"
        )
    try:
        marker = read_marker(directory)
    except MarkerError as error:
        raise WorkspaceError(str(error)) from None
    if marker.schema > SCHEMA_VERSION:
        raise WorkspaceError(
            f"the workspace at {directory} uses schema {marker.schema} "
            f"(created with cstudy {marker.created_with}); "
            f"this cstudy reads schema {SCHEMA_VERSION}: upgrade cstudy"
        )
    return directory


def catalog_cache_directory(environ: Mapping[str, str], home: Path) -> Path:
    """Where `cstudy list` and `cstudy show` cache outside a workspace."""
    cache = environ.get(CACHE_VARIABLE, "")
    base = Path(cache) if cache else home / DEFAULT_CACHE_DIRECTORY
    return base / APPLICATION_DIRECTORY / CATALOG_CACHE


def _explicit_content(path: Path) -> Path:
    root = path.expanduser().resolve()
    if not is_content_root(root):
        markers = " and ".join(f"{marker}/" for marker in CONTENT_MARKERS)
        raise ContentRootError(f"{CONTENT_VARIABLE}={path} needs {markers}")
    return root


def _upward(directory: Path) -> tuple[Path, ...]:
    resolved = directory.resolve()
    return (resolved, *resolved.parents)


class FsRepositoryFiles:
    """`RepositoryFiles` under one root: a workspace or a content root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def exists(self, relative_path: str) -> bool:
        return (self._root / relative_path).exists()
