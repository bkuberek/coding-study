"""The `.vscode/` files of a workspace (docs/specs/installation-and-workspaces.md#ide-files)."""

import json
import re
from typing import Any

import pytest

from coding_study.adapters.ide.vscode import VsCodeProject

TASKS = ".vscode/tasks.json"
LAUNCH = ".vscode/launch.json"
SETTINGS = ".vscode/settings.json"
EXTENSIONS = ".vscode/extensions.json"
FILES = {file.path: file.content for file in VsCodeProject().files()}
READY_LINE = "cstudy: waiting for debugger on 127.0.0.1:5678 (python)"


def document(path: str) -> dict[str, Any]:
    return json.loads(FILES[path])


def tasks() -> dict[str, dict[str, Any]]:
    return {task["label"]: task for task in document(TASKS)["tasks"]}


def launch_configurations() -> dict[str, dict[str, Any]]:
    return {entry["name"]: entry for entry in document(LAUNCH)["configurations"]}


def test_the_project_files_are_tasks_launch_settings_and_extensions():
    assert set(FILES) == {TASKS, LAUNCH, SETTINGS, EXTENSIONS}


@pytest.mark.parametrize("path", [TASKS, LAUNCH, SETTINGS, EXTENSIONS])
def test_each_file_is_json(path):
    assert isinstance(document(path), dict)


@pytest.mark.parametrize("path", [TASKS, LAUNCH, SETTINGS, EXTENSIONS])
def test_each_file_ends_with_a_newline(path):
    assert FILES[path].endswith("}\n")


def test_files_are_indented_with_two_spaces():
    assert FILES[TASKS].splitlines()[1].startswith('  "version"')


def test_rendering_twice_gives_the_same_files():
    assert VsCodeProject().files() == VsCodeProject().files()


def test_a_current_file_task_runs_cstudy_on_the_file():
    task = tasks()["cstudy test (current file)"]
    assert (task["type"], task["command"], task["args"]) == (
        "process",
        "cstudy",
        ["test", "${file}"],
    )


def test_an_active_attempt_task_has_no_target():
    assert tasks()["cstudy test --perf (active attempt)"]["args"] == ["test", "--perf"]


def test_a_workspace_task_runs_its_command():
    assert tasks()["cstudy doctor"]["args"] == ["doctor"]


def test_every_task_runs_in_the_workspace_folder():
    folders = {task["options"]["cwd"] for task in tasks().values()}
    assert folders == {"${workspaceFolder}"}


def test_no_task_asks_how_to_scan_its_output():
    assert all("problemMatcher" in task for task in tasks().values())


def test_done_asks_for_the_outcome():
    assert tasks()["cstudy done (current file)"]["args"] == [
        "done",
        "${input:cstudy-done}",
        "${file}",
    ]


def test_the_outcome_prompt_offers_every_outcome():
    prompt = next(entry for entry in document(TASKS)["inputs"] if entry["id"] == "cstudy-done")
    values = [option["value"] for option in prompt["options"]]
    assert values == ["--rating=ok", "--rating=easy", "--rating=hard", "--gave-up"]


def test_every_prompt_a_task_uses_is_defined():
    used = {
        match
        for task in tasks().values()
        for argument in task["args"]
        for match in re.findall(r"\$\{input:([^}]+)\}", argument)
    }
    defined = {entry["id"] for entry in document(TASKS)["inputs"]}
    assert used == defined


def test_the_debug_task_keeps_running_in_the_background():
    assert tasks()["cstudy test --debug (current file)"]["isBackground"] is True


def test_the_debug_task_is_ready_when_cstudy_waits_for_the_debugger():
    background = tasks()["cstudy test --debug (current file)"]["problemMatcher"]["background"]
    assert re.search(background["endsPattern"], READY_LINE)


def test_the_debug_task_starts_active():
    background = tasks()["cstudy test --debug (active attempt)"]["problemMatcher"]["background"]
    assert background["activeOnStart"] is True


@pytest.mark.parametrize(
    ("name", "debugger", "port"),
    [
        ("Debug current file (Python)", "debugpy", 5678),
        ("Debug current file (TypeScript)", "node", 9229),
        ("Debug current file (Java)", "java", 5005),
        ("Debug active attempt (Python)", "debugpy", 5678),
    ],
)
def test_each_language_attaches_its_debugger_on_its_port(name, debugger, port):
    configuration = launch_configurations()[name]
    attached = configuration.get("connect", configuration).get("port")
    assert (configuration["type"], configuration["request"], attached) == (
        debugger,
        "attach",
        port,
    )


def test_debuggers_attach_on_loopback():
    hosts = {
        configuration.get("connect", {}).get("host")
        or configuration.get("address")
        or configuration.get("hostName")
        for configuration in launch_configurations().values()
    }
    assert hosts == {"127.0.0.1"}


def test_kotlin_cannot_be_debugged_in_vscode():
    assert not [name for name in launch_configurations() if "Kotlin" in name]


def test_every_debug_configuration_first_starts_cstudy_in_debug_mode():
    started = {configuration["preLaunchTask"] for configuration in launch_configurations().values()}
    assert started == {"cstudy test --debug (current file)", "cstudy test --debug (active attempt)"}


def test_python_uses_the_workspace_venv():
    interpreter = document(SETTINGS)["python.defaultInterpreterPath"]
    assert interpreter == "${workspaceFolder}/python/.venv/bin/python"


def test_typescript_uses_the_workspace_compiler():
    assert document(SETTINGS)["typescript.tsdk"] == "typescript/node_modules/typescript/lib"


def test_the_jvm_project_is_imported_with_gradle():
    assert document(SETTINGS)["java.import.gradle.enabled"] is True


def test_the_settings_never_pin_a_jdk():
    assert "java.jdt.ls.java.home" not in document(SETTINGS)


def test_the_extensions_for_python_and_the_jvm_are_recommended():
    assert document(EXTENSIONS)["recommendations"] == [
        "ms-python.python",
        "ms-python.debugpy",
        "vscjava.vscode-java-pack",
        "vscjava.vscode-gradle",
    ]
