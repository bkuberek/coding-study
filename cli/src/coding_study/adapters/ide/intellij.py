"""The `.idea/` files of a workspace (docs/specs/installation-and-workspaces.md#ide-files).

- `misc.xml` names the project JDK after the JVM toolchain of the practice projects, and
  `gradle.xml` links `jvm/` as a Gradle project run with that JDK.
- `runConfigurations/` holds shared run configurations. Actions on the file in the editor start
  the launcher jar, because JAR Application configurations expand `$FilePath$` and Shell Script
  ones expand no macro; actions on the active attempt and on the workspace are Shell Script
  commands run in the terminal. Java and Kotlin debugging is a Remote JVM Debug configuration
  listening for the JVM that `cstudy test --debug --debug-connect` starts, both launched by a
  compound configuration.

ElementTree serializes every file in IntelliJ's own layout (two-space indents, attributes in
IntelliJ's order, a final newline), so generating it again gives the same bytes.
"""

import re
import shlex
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass

from coding_study.adapters.ide.launcher import LAUNCHER_IN_RUNTIME
from coding_study.adapters.runner_runtime import RUNTIME_DIRECTORY
from coding_study.domain.ide import GeneratedFile, Ide
from coding_study.domain.ide_actions import (
    BOTH_SCOPES,
    DEBUG_CONNECT,
    EXECUTABLE,
    JDWP_PORT,
    JVM,
    PROBLEM_ACTIONS,
    WORKSPACE_ACTIONS,
    ProblemAction,
    Scope,
    Variant,
    debug_name,
)
from coding_study.domain.layout import JVM_PROJECT

DIRECTORY = Ide.IDEA.directory
RUN_CONFIGURATIONS = f"{DIRECTORY}/runConfigurations"
PROJECT_DIR = "$PROJECT_DIR$"
CURRENT_FILE = "$FilePath$"
"""Expanded when the configuration starts; the project directory when no editor has focus."""
LAUNCHER = f"{PROJECT_DIR}/{RUNTIME_DIRECTORY}/{LAUNCHER_IN_RUNTIME}"
JDK_VERSION = 21
"""The JVM toolchain of the practice projects (`JAVA_VERSION` in the runners' PracticePlugin)."""
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'
INDENT = "  "
FILE_NAME_UNSAFE = re.compile(r"[^A-Za-z0-9_]")
"""IntelliJ names a shared configuration's file after it with every other character as `_`;
the same name keeps it from renaming the file when it saves the configuration."""
JAR_APPLICATION = "JarApplication"
SHELL_SCRIPT = "ShConfigurationType"
REMOTE = "Remote"
COMPOUND = "CompoundRunConfigurationType"
FOLDERS = {
    Scope.CURRENT_FILE: "cstudy: current file",
    Scope.ACTIVE_ATTEMPT: "cstudy: active attempt",
}
WORKSPACE_FOLDER = "cstudy: workspace"
DEBUG_FOLDER = "cstudy: debug"
LISTENER_NAME = "Debug JVM (listen)"
"""`cstudy test --debug --debug-connect` tells you to start it by this name when nothing
listens."""
LISTENER_HOST = "localhost"
TRUE = "true"
FALSE = "false"


@dataclass(frozen=True, slots=True)
class _Configuration:
    name: str
    type: str
    folder: str
    body: tuple[ET.Element, ...]

    def file(self) -> GeneratedFile:
        component = ET.Element("component", name="ProjectRunConfigurationManager")
        attributes = {"default": FALSE, "name": self.name, "type": self.type}
        configuration = ET.SubElement(
            component, "configuration", {**attributes, "folderName": self.folder}
        )
        configuration.extend(self.body)
        ET.SubElement(configuration, "method", v="2")
        file_name = FILE_NAME_UNSAFE.sub("_", self.name)
        return GeneratedFile(f"{RUN_CONFIGURATIONS}/{file_name}.xml", _serialized(component))


class IntellijProject:
    def files(self) -> tuple[GeneratedFile, ...]:
        configurations = (*_action_configurations(), *_debug_configurations())
        return (
            GeneratedFile(f"{DIRECTORY}/misc.xml", _project_file(_misc())),
            GeneratedFile(f"{DIRECTORY}/gradle.xml", _project_file(_gradle())),
            *(configuration.file() for configuration in configurations),
        )


def _misc() -> ET.Element:
    project = ET.Element("project", version="4")
    ET.SubElement(
        project, "component", {"name": "ExternalStorageConfigurationManager", "enabled": TRUE}
    )
    ET.SubElement(
        project,
        "component",
        {
            "name": "ProjectRootManager",
            "version": "2",
            "languageLevel": f"JDK_{JDK_VERSION}",
            "project-jdk-name": str(JDK_VERSION),
            "project-jdk-type": "JavaSDK",
        },
    )
    return project


def _gradle() -> ET.Element:
    project = ET.Element("project", version="4")
    ET.SubElement(
        project, "component", {"name": "GradleMigrationSettings", "migrationVersion": "1"}
    )
    settings = ET.SubElement(project, "component", name="GradleSettings")
    linked = ET.SubElement(settings, "option", name="linkedExternalProjectsSettings")
    gradle_project = ET.SubElement(linked, "GradleProjectSettings")
    jvm_project = f"{PROJECT_DIR}/{JVM_PROJECT}"
    gradle_project.extend(
        _options(("externalProjectPath", jvm_project), ("gradleJvm", "#USE_PROJECT_JDK"))
    )
    modules = ET.SubElement(ET.SubElement(gradle_project, "option", name="modules"), "set")
    for module in (jvm_project, *(f"{jvm_project}/{language}" for language in JVM)):
        ET.SubElement(modules, "option", value=module)
    return project


def _action_configurations() -> Iterator[_Configuration]:
    for action in (*PROBLEM_ACTIONS, DEBUG_CONNECT):
        for scope in action.scopes:
            for variant in action.each_variant():
                yield _action_configuration(action, scope, variant)
    for workspace_action in WORKSPACE_ACTIONS:
        yield _Configuration(
            workspace_action.name,
            SHELL_SCRIPT,
            WORKSPACE_FOLDER,
            _shell(workspace_action.arguments),
        )


def _action_configuration(
    action: ProblemAction, scope: Scope, variant: Variant | None
) -> _Configuration:
    arguments = action.invocation(scope, CURRENT_FILE, variant.argument if variant else None)
    name = action.name(scope, variant)
    if scope is Scope.CURRENT_FILE:
        return _Configuration(name, JAR_APPLICATION, FOLDERS[scope], _launcher(arguments))
    return _Configuration(name, SHELL_SCRIPT, FOLDERS[scope], _shell(arguments))


def _debug_configurations() -> Iterator[_Configuration]:
    """The listener, and per scope a compound starting it with cstudy."""
    listener = _listener()
    yield listener
    for scope in BOTH_SCOPES:
        yield _compound(debug_name(scope, JVM), listener, scope)


def _listener() -> _Configuration:
    options = _options(
        ("USE_SOCKET_TRANSPORT", TRUE),
        ("SERVER_MODE", TRUE),
        ("SHMEM_ADDRESS", None),
        ("HOST", LISTENER_HOST),
        ("PORT", str(JDWP_PORT)),
        ("AUTO_RESTART", TRUE),
    )
    return _Configuration(LISTENER_NAME, REMOTE, DEBUG_FOLDER, options)


def _compound(name: str, listener: _Configuration, scope: Scope) -> _Configuration:
    run = _action_configuration(DEBUG_CONNECT, scope, None)
    parts = tuple(ET.Element("toRun", name=part.name, type=part.type) for part in (listener, run))
    return _Configuration(name, COMPOUND, DEBUG_FOLDER, parts)


def _launcher(arguments: tuple[str, ...]) -> tuple[ET.Element, ...]:
    """IntelliJ splits the expanded parameters at spaces outside double quotes, and a file path
    may hold spaces."""
    parameters = " ".join(
        f'"{argument}"' if argument == CURRENT_FILE else argument for argument in arguments
    )
    return _options(
        ("JAR_PATH", LAUNCHER),
        ("PROGRAM_PARAMETERS", parameters),
        ("WORKING_DIRECTORY", PROJECT_DIR),
        ("ALTERNATIVE_JRE_PATH_ENABLED", FALSE),
        ("ALTERNATIVE_JRE_PATH", None),
    )


def _shell(arguments: tuple[str, ...]) -> tuple[ET.Element, ...]:
    options = _options(
        ("SCRIPT_TEXT", shlex.join((EXECUTABLE, *arguments))),
        ("INDEPENDENT_SCRIPT_PATH", TRUE),
        ("SCRIPT_PATH", ""),
        ("SCRIPT_OPTIONS", ""),
        ("INDEPENDENT_SCRIPT_WORKING_DIRECTORY", TRUE),
        ("SCRIPT_WORKING_DIRECTORY", PROJECT_DIR),
        ("INDEPENDENT_INTERPRETER_PATH", TRUE),
        ("INTERPRETER_PATH", ""),
        ("EXECUTE_IN_TERMINAL", TRUE),
        ("EXECUTE_SCRIPT_FILE", FALSE),
    )
    return (*options, ET.Element("envs"))


def _options(*pairs: tuple[str, str | None]) -> tuple[ET.Element, ...]:
    """`<option name=… value=… />`; a None value leaves the attribute out, as IntelliJ does for
    an unset string."""
    return tuple(
        ET.Element("option", {"name": name} if value is None else {"name": name, "value": value})
        for name, value in pairs
    )


def _project_file(project: ET.Element) -> str:
    return XML_DECLARATION + _serialized(project)


def _serialized(root: ET.Element) -> str:
    ET.indent(root, space=INDENT)
    return ET.tostring(root, encoding="unicode") + "\n"
