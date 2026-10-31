"""The Rust rows of `cstudy doctor`
(docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace): every Rust project folder
reaches the vendored crates through its `.cargo/config.toml`, and rust-analyzer links its
`Cargo.toml`."""

import json
import tomllib
from collections.abc import Container
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from coding_study.adapters.ide.vscode import LINKED_PROJECTS
from coding_study.application.ports import FolderCheck
from coding_study.domain.ide import Ide
from coding_study.domain.workspace_projects import (
    CARGO_CONFIG_FILE,
    CARGO_MANIFEST,
    PROJECTS_DIRECTORY,
    RUST_CARGO_CONFIG,
)

CONFIG_CHECK = "rust project config"
CONFIG_PROBLEM = f"missing or unresolved {CARGO_CONFIG_FILE}"
LINKED_CHECK = "rust linked projects"
LINKED_PROBLEM = f"missing from {LINKED_PROJECTS}"
IDE_COMMAND = "cstudy ide"
VSCODE_SETTINGS = f"{Ide.VSCODE.directory}/settings.json"


@dataclass(frozen=True, slots=True)
class RustFolderChecks:
    """The folder checks of one workspace root."""

    root: Path

    def folder_checks(self) -> tuple[FolderCheck, ...]:
        """The config row always; the linked-projects row only with a VS Code settings file."""
        folders = self._folders()
        unresolved = tuple(folder for folder in folders if not self._reaches_vendor(folder))
        config = FolderCheck(CONFIG_CHECK, unresolved, CONFIG_PROBLEM)
        linked = self._linked_projects()
        if linked is None:
            return (config,)
        unlinked = tuple(folder for folder in folders if f"{folder}/{CARGO_MANIFEST}" not in linked)
        return config, FolderCheck(LINKED_CHECK, unlinked, LINKED_PROBLEM, IDE_COMMAND)

    def repair_folders(self) -> tuple[str, ...]:
        """Writes the config of every folder without one; a file, a link or a `.cargo` that is
        not a directory stays as it is."""
        return tuple(
            f"{folder}/{CARGO_CONFIG_FILE}"
            for folder in self._folders()
            if self._write_missing_config(self.root / folder)
        )

    def _folders(self) -> tuple[str, ...]:
        projects = self.root / PROJECTS_DIRECTORY
        if not projects.is_dir():
            return ()
        return tuple(
            f"{PROJECTS_DIRECTORY}/{folder.name}"
            for folder in sorted(projects.iterdir())
            if (folder / CARGO_MANIFEST).is_file()
        )

    def _reaches_vendor(self, folder: str) -> bool:
        """Cargo resolves a source `directory` from the folder holding `.cargo`."""
        directory = _replacement_directory(self.root / folder / CARGO_CONFIG_FILE)
        return directory is not None and (self.root / folder / directory).is_dir()

    def _linked_projects(self) -> Container[str] | None:
        """None without the settings file; nothing linked when it is not the JSON `cstudy ide`
        writes."""
        settings = self.root / VSCODE_SETTINGS
        if not settings.is_file():
            return None
        try:
            linked = json.loads(settings.read_text()).get(LINKED_PROJECTS)
        except (ValueError, AttributeError, OSError):
            return ()
        if not isinstance(linked, list):
            return ()
        return frozenset(entry for entry in cast(list[object], linked) if isinstance(entry, str))

    @staticmethod
    def _write_missing_config(folder: Path) -> bool:
        config = folder / CARGO_CONFIG_FILE
        if config.exists() or config.is_symlink() or config.parent.is_symlink():
            return False
        if config.parent.exists() and not config.parent.is_dir():
            return False
        config.parent.mkdir(exist_ok=True)
        config.write_text(RUST_CARGO_CONFIG)
        return True


def _replacement_directory(config: Path) -> str | None:
    """The `directory` of the source that replaces crates.io; None when there is none."""
    try:
        sources = tomllib.loads(config.read_text()).get("source", {})
        replacement = sources["crates-io"]["replace-with"]
        directory = sources[replacement]["directory"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return directory if isinstance(directory, str) else None
