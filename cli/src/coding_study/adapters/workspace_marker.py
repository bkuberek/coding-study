"""`.cs/workspace.toml`, the file that makes a directory a workspace
(docs/specs/installation-and-workspaces.md#marker)."""

import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

MARKER_FILE = ".cs/workspace.toml"
SCHEMA_VERSION = 1
"""The workspace layout this `cstudy` reads and writes."""
DISTRIBUTION = "coding-study"
UNKNOWN_VERSION = "unknown"


class MarkerError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WorkspaceMarker:
    schema: int
    created_with: str


def tool_version() -> str:
    """The installed `coding-study` version; `unknown` when cstudy runs from sources only."""
    try:
        return metadata.version(DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return UNKNOWN_VERSION


def has_marker(directory: Path) -> bool:
    return (directory / MARKER_FILE).is_file()


def read_marker(directory: Path) -> WorkspaceMarker:
    """Raises MarkerError when the marker is missing, not TOML, or lacks its keys."""
    path = directory / MARKER_FILE
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise MarkerError(f"{path}: {error}") from None
    schema, created_with = document.get("schema"), document.get("created_with")
    if not isinstance(schema, int) or isinstance(schema, bool) or not isinstance(created_with, str):
        raise MarkerError(f"{path}: needs an integer schema and a created_with string")
    return WorkspaceMarker(schema, created_with)


def marker_text(marker: WorkspaceMarker) -> str:
    return (
        "# coding-study workspace (docs/specs/installation-and-workspaces.md); "
        "keep it in version control.\n"
        f"schema = {marker.schema}\n"
        f'created_with = "{marker.created_with}"\n'
    )
