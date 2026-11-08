"""`.cs/workspace.toml`, the file that makes a directory a workspace
(docs/specs/installation-and-workspaces.md#marker)."""

import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import cast

MARKER_FILE = ".cs/workspace.toml"
SCHEMA_VERSION = 1
"""The workspace layout this `cstudy` reads and writes."""
DISTRIBUTION = "coding-study"
UNKNOWN_VERSION = "unknown"
LICENSES_TABLE = "licenses"
"""The licenses you accepted for the servers whose vendor asks for it, by their key."""


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


def accepted_license(directory: Path, key: str) -> tuple[str, str] | None:
    """The name and link of the license the marker records as accepted under `key`; None when
    it records none, or the marker is missing or unreadable."""
    try:
        document = tomllib.loads((directory / MARKER_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    licenses = _table(document.get(LICENSES_TABLE))
    recorded = _table(licenses.get(key))
    name, url = recorded.get("name"), recorded.get("url")
    return (name, url) if isinstance(name, str) and isinstance(url, str) else None


def _table(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def record_license(directory: Path, key: str, name: str, url: str) -> None:
    """Records in the marker, a file you keep in version control, that you accepted the license
    named `name` at `url`, as `[licenses.<key>]`, in place of what it recorded under `key`; the
    rest of the marker stays as it was. Raises OSError, and MarkerError for a marker that does not
    parse."""
    # Imported here: only accepting a license edits the marker, and every command reads it.
    import tomlkit
    from tomlkit.exceptions import ParseError

    path = directory / MARKER_FILE
    try:
        document = tomlkit.parse(path.read_text(encoding="utf-8"))
    except ParseError as error:
        raise MarkerError(f"{path}: {error}") from None
    licenses = document.setdefault(LICENSES_TABLE, tomlkit.table(is_super_table=True))
    licenses[key] = {"name": name, "url": url}
    path.write_text(tomlkit.dumps(document), encoding="utf-8")


def marker_text(marker: WorkspaceMarker) -> str:
    return (
        "# coding-study workspace (docs/specs/installation-and-workspaces.md); "
        "keep it in version control.\n"
        f"schema = {marker.schema}\n"
        f'created_with = "{marker.created_with}"\n'
    )
