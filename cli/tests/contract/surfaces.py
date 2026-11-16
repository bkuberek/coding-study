"""The public surfaces as the code has them now, each a flat mapping from an entry to its value."""

import tomllib
from collections.abc import Iterable
from pathlib import Path

import typer.main
from typer._click import Command
from typer.core import TyperGroup, TyperOption

from coding_study.adapters.toml_config import CONFIG_KEYS
from coding_study.adapters.workspace_marker import (
    LICENSES_TABLE,
    MARKER_FILE,
    SCHEMA_VERSION,
    WorkspaceMarker,
    marker_text,
    record_license,
)
from coding_study.domain import environment_variables
from coding_study.domain.deprecations import DEPRECATIONS, Deprecation, is_deprecated_flag
from coding_study.domain.doc_checks import CommandSpec
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.command_table import command_spec
from coding_study.entrypoints.shared import ExitCode
from tests.contract.snapshot_files import Surface

PROGRAM = "cstudy"
TOML_TYPES: dict[type, str] = {str: "string", int: "integer", bool: "boolean", list: "array"}
LICENSE_KEY = "<key>"
"""The name of the table `[licenses.<key>]` stands for."""


def commands(registry: Iterable[Deprecation] = DEPRECATIONS) -> Surface:
    """Each command and subcommand by its path, and each flag by its path and name."""
    root = typer.main.get_command(cli.app)
    surface: dict[str, object] = {}
    _add_command(surface, PROGRAM, command_spec(root), root, tuple(registry))
    return surface


def _add_command(
    surface: dict[str, object],
    path: str,
    spec: CommandSpec,
    command: Command,
    registry: tuple[Deprecation, ...],
) -> None:
    surface[path] = {"subcommands": sorted(spec.subcommands)}
    choices = _choices(command)
    for name, takes_value in spec.options.items():
        surface[f"{path} {name}"] = {
            "takes_value": takes_value,
            "choices": choices.get(name, []),
            "deprecated": is_deprecated_flag(path, name, registry),
        }
    if isinstance(command, TyperGroup):
        for name, subspec in spec.subcommands.items():
            _add_command(surface, f"{path} {name}", subspec, command.commands[name], registry)


def _choices(command: Command) -> dict[str, list[str]]:
    """The values each flag of `command` accepts, for the flags that take one of a fixed set."""
    names: dict[str, list[str]] = {}
    for parameter in command.params:
        values = getattr(parameter.type, "choices", None)
        if isinstance(parameter, TyperOption) and values:
            for name in (*parameter.opts, *parameter.secondary_opts):
                names[name] = [str(value) for value in values]
    return names


def exit_codes() -> Surface:
    return {code.name: code.value for code in ExitCode}


def config_keys() -> Surface:
    return {
        key.name: {
            "kind": key.kind.value,
            "default": key.default,
            "choices": list(key.choices),
            "reserved": key.reserved,
            "preview": key.preview,
        }
        for key in CONFIG_KEYS
    }


def environment() -> Surface:
    classes = {
        "public": environment_variables.PUBLIC,
        "problem_format": environment_variables.PROBLEM_FORMAT,
        "internal": environment_variables.INTERNAL,
    }
    return {name: kind for kind, names in classes.items() for name in names}


def marker(directory: Path) -> Surface:
    """The marker as `cstudy` writes it, with chosen languages and one accepted license, read back
    from the file: its keys and their types, the keys of a license, and the schema version."""
    (directory / MARKER_FILE).parent.mkdir(parents=True, exist_ok=True)
    (directory / MARKER_FILE).write_text(
        marker_text(WorkspaceMarker(SCHEMA_VERSION, "0.0.0", (Language.PYTHON, Language.GO))),
        encoding="utf-8",
    )
    record_license(directory, LICENSE_KEY, "Name", "https://example.com/license")
    document = tomllib.loads((directory / MARKER_FILE).read_text(encoding="utf-8"))
    surface: dict[str, object] = {"file": MARKER_FILE, "schema_version": SCHEMA_VERSION}
    for key, value in document.items():
        if key == LICENSES_TABLE:
            for license_key, recorded in value.items():
                for field, field_value in recorded.items():
                    surface[f"{key}.{license_key}.{field}"] = _type_name(field_value)
        else:
            surface[f"key.{key}"] = _type_name(value)
    return surface


def _type_name(value: object) -> str:
    """The TOML name of the type of `value`."""
    return TOML_TYPES[type(value)]
