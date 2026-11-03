"""The `cstudy` installs on `PATH`, read from the file system alone: each install's version comes
from the package metadata in its own site-packages, so no copy is started
(docs/specs/cli.md#cstudy-doctor)."""

import os
import tomllib
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import cast

from coding_study.application.installs import (
    DISTRIBUTION,
    Install,
    InstallKind,
    InstallRoots,
    InstallScan,
    classify_install,
)

EXECUTABLE_NAMES = ("cstudy", "cstudy.exe")
SITE_PACKAGES = ("lib/python*/site-packages", "Lib/site-packages")
METADATA_DIRECTORY = f"{DISTRIBUTION.replace('-', '_')}-*.dist-info"
UV_RECEIPT = "uv-receipt.toml"
LOCAL_SOURCES = ("editable", "directory")
"""How uv's receipt names a requirement installed from a directory, and whether it is editable
(the first one)."""


class PathCstudyInstalls:
    def __init__(
        self, environ: Mapping[str, str], home: Path, running_prefix: Path, running_version: str
    ) -> None:
        self._environ = environ
        self._home = home
        self._running_prefix = running_prefix
        self._running_version = running_version

    def scan(self) -> InstallScan:
        roots = self._roots()
        installs = tuple(self._on_path(roots))
        prefix = self._running_prefix.resolve()
        running = next(
            (install for install in installs if install.prefix == prefix),
            _install(prefix, None, roots, self._running_version),
        )
        return InstallScan(installs, running, self._home)

    def _on_path(self, roots: InstallRoots) -> Iterator[Install]:
        seen_directories: set[Path] = set()
        seen_executables: set[Path] = set()
        for entry in self._environ.get("PATH", "").split(os.pathsep):
            if not entry:
                continue
            directory = Path(entry)
            resolved_directory = directory.resolve()
            if resolved_directory in seen_directories:
                continue
            seen_directories.add(resolved_directory)
            for executable in _executables(directory):
                resolved = executable.resolve()
                if resolved in seen_executables:
                    continue
                seen_executables.add(resolved)
                yield _install(resolved.parent.parent, executable, roots, None)

    def _roots(self) -> InstallRoots:
        """uv and pipx honour an environment variable, then the XDG data directory (uv, pipx),
        then their usual places."""
        home = self._home
        named = {name: Path(value) for name, value in self._environ.items() if value}
        data = named.get("XDG_DATA_HOME")
        return InstallRoots(
            uv_tools=_resolved(
                named.get("UV_TOOL_DIR"),
                data and data / "uv" / "tools",
                home / ".local" / "share" / "uv" / "tools",
            ),
            pipx_homes=_resolved(
                named.get("PIPX_HOME"),
                data and data / "pipx",
                home / ".local" / "pipx",
                home / "Library" / "Application Support" / "pipx",
            ),
        )


def _resolved(*candidates: Path | None) -> tuple[Path, ...]:
    return tuple(dict.fromkeys(path.resolve() for path in candidates if path))


def _executables(directory: Path) -> Iterator[Path]:
    for name in EXECUTABLE_NAMES:
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            yield candidate


def _install(
    prefix: Path, executable: Path | None, roots: InstallRoots, version: str | None
) -> Install:
    kind = classify_install(prefix, roots)
    source, editable = _uv_source(prefix) if kind is InstallKind.UV_TOOL else (None, False)
    return Install(
        kind, prefix, executable, version or _installed_version(prefix), source, editable
    )


def _installed_version(prefix: Path) -> str | None:
    """The `Version` of the `coding-study` metadata in the environment's site-packages."""
    for pattern in SITE_PACKAGES:
        for site in sorted(prefix.glob(pattern)):
            for dist_info in sorted(site.glob(METADATA_DIRECTORY)):
                version = _metadata_version(dist_info / "METADATA")
                if version is not None:
                    return version
    return None


def _metadata_version(metadata: Path) -> str | None:
    try:
        lines = metadata.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for line in lines:
        if not line:
            return None
        name, _, value = line.partition(":")
        if name == "Version":
            return value.strip() or None
    return None


def _uv_source(prefix: Path) -> tuple[Path | None, bool]:
    """The directory a uv tool was installed from, and whether it is editable, as the tool's
    receipt records it; none for a tool installed from an index."""
    try:
        receipt = tomllib.loads((prefix / UV_RECEIPT).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None, False
    tool = receipt.get("tool")
    requirements = (
        cast(dict[str, object], tool).get("requirements") if isinstance(tool, dict) else None
    )
    for requirement in cast(list[object], requirements) if isinstance(requirements, list) else []:
        if not isinstance(requirement, dict):
            continue
        fields = cast(dict[str, object], requirement)
        if fields.get("name") != DISTRIBUTION:
            continue
        for key in LOCAL_SOURCES:
            value = fields.get(key)
            if isinstance(value, str):
                return Path(value), key == LOCAL_SOURCES[0]
    return None, False
