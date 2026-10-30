"""The `.vscode/` files of a workspace (docs/specs/installation-and-workspaces.md#ide-files).

Tasks run `cstudy` on the file in the editor (`${file}`) or on the active attempt; debug
configurations start `cstudy test --debug` as a background task and attach once cstudy prints its
ready line. VS Code cannot debug Kotlin (microsoft/vscode-java-debug#241), so Kotlin has tasks
only. Every file is JSON with a fixed key order, two-space indents and a final newline, so
generating it again gives the same bytes.
"""

import json
from collections.abc import Iterator
from typing import Any, assert_never

from coding_study.domain.debugging import DEBUG_HOST
from coding_study.domain.ide import GeneratedFile, Ide
from coding_study.domain.ide_actions import (
    BOTH_SCOPES,
    DEBUG_ATTACH,
    DEBUG_LISTEN,
    EXECUTABLE,
    PROBLEM_ACTIONS,
    WORKSPACE_ACTIONS,
    Choice,
    DebugAttach,
    ProblemAction,
    Scope,
    debug_name,
)
from coding_study.domain.layout import PYTHON_PROJECT, RUST_PROJECT, TYPESCRIPT_PROJECT
from coding_study.domain.problem import Language

JsonObject = dict[str, Any]

DIRECTORY = Ide.VSCODE.directory
CURRENT_FILE = "${file}"
WORKSPACE_FOLDER = "${workspaceFolder}"
TASKS_VERSION = "2.0.0"
LAUNCH_VERSION = "0.2.0"
INDENT = 2
READY_PATTERN = r"^cstudy: waiting for debugger on 127\.0\.0\.1:\d+"
"""The line cstudy prints once the runner's debug agent listens (cstudy test --debug)."""
NO_PROBLEMS_PATTERN = {
    "regexp": "^cstudy reports no problems$",
    "file": 1,
    "line": 1,
    "message": 1,
}
"""A background task's problem matcher needs a pattern; cstudy reports no file problems."""
NO_PROBLEM_MATCHER: list[Any] = []
"""Without a matcher, VS Code asks how to scan the output each time a task runs."""
SETTINGS: JsonObject = {
    "python.defaultInterpreterPath": f"{WORKSPACE_FOLDER}/{PYTHON_PROJECT}/.venv/bin/python",
    "typescript.tsdk": f"{TYPESCRIPT_PROJECT}/node_modules/typescript/lib",
    "java.import.gradle.enabled": True,
    "go.toolsEnvVars": {"GOTOOLCHAIN": "local"},
    "rust-analyzer.linkedProjects": [f"{RUST_PROJECT}/Cargo.toml"],
    "rust-analyzer.check.allTargets": True,
    "rust-analyzer.check.extraArgs": ["--keep-going"],
    "files.watcherExclude": {
        "**/.gradle/**": True,
        "**/.kotlin/**": True,
        "**/.venv/**": True,
        "**/build/**": True,
        "**/node_modules/**": True,
        "**/target/**": True,
    },
    "search.exclude": {
        "**/.gradle": True,
        "**/.kotlin": True,
        "**/.venv": True,
        "**/build": True,
        "**/node_modules": True,
        "**/target": True,
    },
}
"""The interpreter and compiler of the workspace's own projects. The Java extension finds the
Gradle project in `jvm/` itself; the JDK is left to the user's setup, since
`java.jdt.ls.java.home` would pin a machine-specific path. gopls finds `go/` through the
workspace's `go.work`; the Go tools run with `GOTOOLCHAIN=local`, as `cstudy` does, so they never
download a toolchain. rust-analyzer needs the link because `Cargo.toml` is in `rust/`, checks every
target because each problem is an `[[example]]`, and `--keep-going` keeps one broken problem from
hiding the errors of the others."""
EXTENSIONS: JsonObject = {
    "recommendations": [
        "ms-python.python",
        "ms-python.debugpy",
        "vscjava.vscode-java-pack",
        "vscjava.vscode-gradle",
        "golang.go",
        "rust-lang.rust-analyzer",
        "vadimcn.vscode-lldb",
    ]
}
DEBUGGABLE = (Language.PYTHON, Language.TYPESCRIPT, Language.JAVA, Language.GO, Language.RUST)
"""The languages VS Code attaches to; Kotlin breakpoints never bind (vscode-java-debug#241)."""
EMPTY_TARGET = 'target create ""'
"""CodeLLDB needs a target before it connects; an empty one takes the executable the debug server
reports, since each run launches the runner from a directory of its own."""
KILL_DEBUGGEE = "script None if not lldb.process.is_alive else (lldb.process.Kill() and None)"
"""CodeLLDB detaches from an attached process when its session ends, and the debug server then exits
and leaves the runner going. `preTerminateCommands` run just before that detach. A plain
`process kill` prints `error: Process must be launched.` once the run has finished; this kills only
a live process and prints nothing. Without Python in CodeLLDB it does nothing, and `cstudy test
--debug` kills the runner itself when its task ends."""


class VsCodeProject:
    def files(self) -> tuple[GeneratedFile, ...]:
        return (
            _json_file("tasks.json", _tasks()),
            _json_file("launch.json", _launch()),
            _json_file("settings.json", SETTINGS),
            _json_file("extensions.json", EXTENSIONS),
        )


def _json_file(name: str, document: JsonObject) -> GeneratedFile:
    return GeneratedFile(f"{DIRECTORY}/{name}", json.dumps(document, indent=INDENT) + "\n")


def _tasks() -> JsonObject:
    tasks = [
        *(task for action in PROBLEM_ACTIONS for task in _problem_tasks(action)),
        *(_task(action.name, action.arguments) for action in WORKSPACE_ACTIONS),
        *(_debug_task(scope) for scope in DEBUG_LISTEN.scopes),
    ]
    inputs = [_input(action, action.choice) for action in PROBLEM_ACTIONS if action.choice]
    return {"version": TASKS_VERSION, "tasks": tasks, "inputs": inputs}


def _problem_tasks(action: ProblemAction) -> Iterator[JsonObject]:
    chosen = _input_reference(action) if action.choice else None
    for scope in action.scopes:
        yield _task(action.name(scope), action.invocation(scope, CURRENT_FILE, chosen))


def _task(label: str, arguments: tuple[str, ...]) -> JsonObject:
    return {
        "label": label,
        "type": "process",
        "command": EXECUTABLE,
        "args": list(arguments),
        "options": {"cwd": WORKSPACE_FOLDER},
        "problemMatcher": NO_PROBLEM_MATCHER,
    }


def _debug_task(scope: Scope) -> JsonObject:
    task = _task(DEBUG_LISTEN.name(scope), DEBUG_LISTEN.invocation(scope, CURRENT_FILE))
    task["isBackground"] = True
    task["problemMatcher"] = {
        "owner": EXECUTABLE,
        "pattern": NO_PROBLEMS_PATTERN,
        "background": {
            "activeOnStart": True,
            "beginsPattern": READY_PATTERN,
            "endsPattern": READY_PATTERN,
        },
    }
    return task


def _input_id(action: ProblemAction) -> str:
    return f"{EXECUTABLE}-{action.command}"


def _input_reference(action: ProblemAction) -> str:
    return f"${{input:{_input_id(action)}}}"


def _input(action: ProblemAction, choice: Choice) -> JsonObject:
    options = [{"label": variant.label, "value": variant.argument} for variant in choice.variants]
    return {
        "id": _input_id(action),
        "type": "pickString",
        "description": choice.prompt,
        "options": options,
        "default": choice.variants[0].argument,
    }


def _launch() -> JsonObject:
    attaches = [attach for attach in DEBUG_ATTACH if attach.language in DEBUGGABLE]
    configurations = [_attach(attach, scope) for scope in BOTH_SCOPES for attach in attaches]
    return {"version": LAUNCH_VERSION, "configurations": configurations}


def _attach(attach: DebugAttach, scope: Scope) -> JsonObject:
    common = {
        "name": debug_name(scope, (attach.language,)),
        "request": "attach",
        "preLaunchTask": DEBUG_LISTEN.name(scope),
    }
    return {**common, **_debugger(attach)}


def _debugger(attach: DebugAttach) -> JsonObject:
    match attach.language:
        case Language.PYTHON:
            return {
                "type": "debugpy",
                "connect": {"host": DEBUG_HOST, "port": attach.port},
                "justMyCode": True,
            }
        case Language.TYPESCRIPT:
            return {
                "type": "node",
                "address": DEBUG_HOST,
                "port": attach.port,
                "skipFiles": ["<node_internals>/**"],
            }
        case Language.JAVA:
            return {"type": "java", "hostName": DEBUG_HOST, "port": attach.port}
        case Language.GO:
            return {"type": "go", "mode": "remote", "host": DEBUG_HOST, "port": attach.port}
        case Language.RUST:
            return {
                "type": "lldb",
                "targetCreateCommands": [EMPTY_TARGET],
                "processCreateCommands": [f"gdb-remote {DEBUG_HOST}:{attach.port}"],
                "preTerminateCommands": [KILL_DEBUGGEE],
                "sourceLanguages": ["rust"],
            }
        case Language.KOTLIN:
            raise ValueError(f"no VS Code attach configuration for {attach.language} (DEBUGGABLE)")
        case _:
            assert_never(attach.language)
