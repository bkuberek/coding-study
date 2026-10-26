"""Every command line the IDE files run is one `cstudy` accepts, so renaming an option breaks the
build rather than a run configuration (docs/specs/installation-and-workspaces.md#ide-files)."""

import json
import re
import shlex
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Sequence
from typing import Any

import pytest
import typer
from typer.core import TyperGroup
from typer.main import get_command

from coding_study.adapters.ide.intellij import IntellijProject
from coding_study.adapters.ide.vscode import VsCodeProject
from coding_study.domain.ide_actions import (
    DEBUG_CONNECT,
    DEBUG_LISTEN,
    EXECUTABLE,
    PROBLEM_ACTIONS,
    WORKSPACE_ACTIONS,
)
from coding_study.entrypoints import cli

SOLUTION_FILE = "/home/me/my workspace/python/practice/two_sum.py"
DEBUGGER_OPTIONS = frozenset({"--debug", "--debug-connect"})
"""`cstudy test --debug [--debug-connect]` come with the debugger support built alongside the IDE
files (feature task T2, whose option contract the debug actions follow); parsing leaves out just
these two tokens until both are merged, so every other token of a debug command line is checked."""
INPUT = re.compile(r"\$\{input:([^}]+)\}")


def parse(arguments: Sequence[str]) -> None:
    """Parses `cstudy <arguments>` as a run would, without running it; raises a usage error."""
    group = get_command(cli.app)
    assert isinstance(group, TyperGroup)
    supported = [argument for argument in arguments if argument not in DEBUGGER_OPTIONS]
    context = group.make_context(EXECUTABLE, supported)
    command = group.get_command(context, supported[0])
    if command is None:
        raise typer.BadParameter(f"no command {supported[0]}")
    command.make_context(supported[0], supported[1:], parent=context)


def catalog_command_lines() -> Iterator[tuple[str, ...]]:
    for action in (*PROBLEM_ACTIONS, DEBUG_LISTEN, DEBUG_CONNECT):
        for scope in action.scopes:
            for variant in action.each_variant():
                yield action.invocation(scope, SOLUTION_FILE, variant.argument if variant else None)
    for workspace_action in WORKSPACE_ACTIONS:
        yield workspace_action.arguments


def vscode_command_lines() -> Iterator[tuple[str, ...]]:
    tasks = _vscode_document(".vscode/tasks.json")
    choices = {
        entry["id"]: [option["value"] for option in entry["options"]] for entry in tasks["inputs"]
    }
    for task in tasks["tasks"]:
        assert task["command"] == EXECUTABLE
        yield from _filled_in(task["args"], choices)


def _filled_in(arguments: list[str], choices: dict[str, list[str]]) -> Iterator[tuple[str, ...]]:
    """`arguments` with the current file, once per value of the input they use, if any."""
    filled = [argument.replace("${file}", SOLUTION_FILE) for argument in arguments]
    for position, argument in enumerate(filled):
        if prompt := INPUT.fullmatch(argument):
            for value in choices[prompt[1]]:
                yield (*filled[:position], value, *filled[position + 1 :])
            return
    yield tuple(filled)


def intellij_command_lines() -> Iterator[tuple[str, ...]]:
    for file in IntellijProject().files():
        configuration = ET.fromstring(file.content).find("configuration")
        if configuration is None:
            continue
        values = {option.get("name"): option.get("value") for option in configuration}
        if "PROGRAM_PARAMETERS" in values:
            parameters = str(values["PROGRAM_PARAMETERS"]).replace("$FilePath$", SOLUTION_FILE)
            yield tuple(shlex.split(parameters))
        if "SCRIPT_TEXT" in values:
            executable, *arguments = shlex.split(str(values["SCRIPT_TEXT"]))
            assert executable == EXECUTABLE
            yield tuple(arguments)


def _vscode_document(path: str) -> Any:
    return json.loads(next(file.content for file in VsCodeProject().files() if file.path == path))


@pytest.mark.parametrize("arguments", list(catalog_command_lines()), ids=" ".join)
def test_every_catalog_action_is_a_cstudy_command_line(arguments):
    parse(arguments)


@pytest.mark.parametrize("arguments", list(vscode_command_lines()), ids=" ".join)
def test_every_vscode_task_runs_a_cstudy_command_line(arguments):
    parse(arguments)


@pytest.mark.parametrize("arguments", list(intellij_command_lines()), ids=" ".join)
def test_every_intellij_configuration_runs_a_cstudy_command_line(arguments):
    parse(arguments)


def test_a_renamed_option_fails_the_parse():
    with pytest.raises(typer.TyperException):
        parse(("test", "--perff", SOLUTION_FILE))


def test_a_missing_required_target_fails_the_parse():
    with pytest.raises(typer.TyperException):
        parse(("solution",))
