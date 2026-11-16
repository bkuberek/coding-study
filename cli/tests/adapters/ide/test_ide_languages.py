"""The IDE files of a workspace that chose its languages
(docs/specs/installation-and-workspaces.md#ide-files): three language sets are golden, one for
every language and two narrow ones, and each language's own part is checked alone."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.ide.intellij import IntellijProject
from coding_study.adapters.ide.vscode import VsCodeProject
from coding_study.domain.ide import GeneratedFile, IdeWorkspace
from coding_study.domain.problem import ALL_LANGUAGES, Language

GOLDEN = Path(__file__).parent / "golden" / "all_languages.json"
RUST_FOLDER = "projects/bank-project-rust/Cargo.toml"
TASKS = ".vscode/tasks.json"
LAUNCH = ".vscode/launch.json"
SETTINGS = ".vscode/settings.json"
EXTENSIONS = ".vscode/extensions.json"
MISC = ".idea/misc.xml"
GRADLE = ".idea/gradle.xml"
RUN_CONFIGURATIONS = ".idea/runConfigurations/"
EXCLUSIONS_ORDER = ["files.watcherExclude", "search.exclude"]
FOLDERS = {"cstudy: current file", "cstudy: active attempt", "cstudy: workspace"}
DEBUG_FOLDER = "cstudy: debug"


def render(*languages: Language) -> dict[str, str]:
    workspace = IdeWorkspace((RUST_FOLDER,), languages=languages or ALL_LANGUAGES)
    files: tuple[GeneratedFile, ...] = (
        *VsCodeProject().files(workspace),
        *IntellijProject().files(workspace),
    )
    return {file.path: file.content for file in files}


def document(files: dict[str, str], path: str) -> dict[str, Any]:
    return json.loads(files[path])


def task_labels(files: dict[str, str]) -> set[str]:
    return {task["label"] for task in document(files, TASKS)["tasks"]}


def launch_names(files: dict[str, str]) -> list[str]:
    return [entry["name"] for entry in document(files, LAUNCH)["configurations"]]


def configuration_folders(files: dict[str, str]) -> set[str]:
    roots = (
        ET.fromstring(content)
        for path, content in files.items()
        if path.startswith(RUN_CONFIGURATIONS)
    )
    return {configuration.get("folderName", "") for root in roots for configuration in root}


def configuration_names(files: dict[str, str]) -> set[str]:
    roots = (
        ET.fromstring(content)
        for path, content in files.items()
        if path.startswith(RUN_CONFIGURATIONS)
    )
    return {configuration.get("name", "") for root in roots for configuration in root}


# all six languages: today's bytes


def test_a_workspace_with_all_six_languages_gets_the_bytes_it_always_got():
    files = render(*ALL_LANGUAGES)
    digests = {path: GeneratedFile(path, content).digest for path, content in sorted(files.items())}
    assert digests == json.loads(GOLDEN.read_text())


def test_a_workspace_that_chose_none_is_a_workspace_with_all_six():
    assert render() == render(*ALL_LANGUAGES)


def test_the_order_the_languages_are_listed_in_changes_no_byte():
    assert render(Language.GO, Language.PYTHON) == render(Language.PYTHON, Language.GO)


# python alone


def test_python_alone_gets_its_vscode_files_and_the_language_agnostic_run_configurations():
    files = render(Language.PYTHON)
    assert {path for path in files if not path.startswith(RUN_CONFIGURATIONS)} == {
        TASKS,
        LAUNCH,
        SETTINGS,
        EXTENSIONS,
    }
    assert configuration_folders(files) == FOLDERS


def test_python_alone_gets_no_gradle_project_and_no_jvm_debug_configurations():
    files = render(Language.PYTHON)
    assert {MISC, GRADLE}.isdisjoint(files)
    assert not [name for name in configuration_names(files) if "Debug" in name or "debug" in name]


def test_python_alone_has_no_typecheck_task_and_no_typecheck_run_configuration():
    files = render(Language.PYTHON)
    assert not [label for label in task_labels(files) if "--typecheck" in label]
    assert not [name for name in configuration_names(files) if "--typecheck" in name]


def test_python_alone_debugs_python_in_vscode_only():
    files = render(Language.PYTHON)
    assert launch_names(files) == ["Debug current file (Python)", "Debug active attempt (Python)"]
    assert "cstudy test --debug (current file)" in task_labels(files)


def test_python_alone_sets_the_interpreter_and_recommends_the_python_extensions():
    files = render(Language.PYTHON)
    assert list(document(files, SETTINGS)) == ["python.defaultInterpreterPath", *EXCLUSIONS_ORDER]
    assert document(files, EXTENSIONS) == {
        "recommendations": ["ms-python.python", "ms-python.debugpy"]
    }


# kotlin alone


def test_kotlin_alone_gets_no_launch_file_because_vscode_cannot_debug_it():
    files = render(Language.KOTLIN)
    assert LAUNCH not in files
    assert {path for path in files if path.startswith(".vscode/")} == {TASKS, SETTINGS, EXTENSIONS}


def test_kotlin_alone_gets_no_debug_task_and_no_typecheck_task():
    labels = task_labels(render(Language.KOTLIN))
    assert not [label for label in labels if "--debug" in label or "--typecheck" in label]
    assert "cstudy test (current file)" in labels


def test_kotlin_alone_is_imported_with_gradle_in_both_editors():
    files = render(Language.KOTLIN)
    assert list(document(files, SETTINGS)) == ["java.import.gradle.enabled", *EXCLUSIONS_ORDER]
    assert document(files, EXTENSIONS) == {
        "recommendations": ["vscjava.vscode-java-pack", "vscjava.vscode-gradle"]
    }
    assert {MISC, GRADLE} <= set(files)


def test_kotlin_alone_gets_the_jvm_debug_configurations_of_intellij():
    files = render(Language.KOTLIN)
    assert configuration_folders(files) == {*FOLDERS, DEBUG_FOLDER}
    assert "Debug JVM (listen)" in configuration_names(files)


# each language's own part


@pytest.mark.parametrize(
    ("language", "keys", "extensions"),
    [
        (
            Language.PYTHON,
            ["python.defaultInterpreterPath"],
            ["ms-python.python", "ms-python.debugpy"],
        ),
        (Language.TYPESCRIPT, ["typescript.tsdk"], []),
        (
            Language.JAVA,
            ["java.import.gradle.enabled"],
            ["vscjava.vscode-java-pack", "vscjava.vscode-gradle"],
        ),
        (
            Language.KOTLIN,
            ["java.import.gradle.enabled"],
            ["vscjava.vscode-java-pack", "vscjava.vscode-gradle"],
        ),
        (Language.GO, ["go.toolsEnvVars"], ["golang.go"]),
        (
            Language.RUST,
            ["rust-analyzer.linkedProjects", "rust-analyzer.check.allTargets"],
            ["rust-lang.rust-analyzer", "vadimcn.vscode-lldb"],
        ),
    ],
)
def test_a_language_brings_its_own_settings_and_extensions(language, keys, extensions):
    files = render(language)
    assert list(document(files, SETTINGS)) == [*keys, *EXCLUSIONS_ORDER]
    assert document(files, EXTENSIONS) == {"recommendations": extensions}


@pytest.mark.parametrize(
    ("language", "debugs"),
    [
        (Language.PYTHON, True),
        (Language.TYPESCRIPT, True),
        (Language.JAVA, True),
        (Language.KOTLIN, False),
        (Language.GO, True),
        (Language.RUST, True),
    ],
)
def test_vscode_debug_tasks_and_launch_file_follow_the_languages_it_debugs(language, debugs):
    files = render(language)
    assert (LAUNCH in files, "cstudy test --debug (current file)" in task_labels(files)) == (
        debugs,
        debugs,
    )


@pytest.mark.parametrize("language", ALL_LANGUAGES)
def test_each_language_gets_the_tasks_of_the_language_agnostic_actions(language):
    labels = task_labels(render(language))
    assert {"cstudy test (current file)", "cstudy done (active attempt)", "cstudy doctor"} <= labels


def test_the_typecheck_tasks_come_with_typescript():
    labels = task_labels(render(Language.TYPESCRIPT))
    assert {
        "cstudy test --typecheck (current file, TypeScript)",
        "cstudy test --typecheck (active attempt, TypeScript)",
    } <= labels


def test_every_prompt_a_task_uses_is_defined_whichever_actions_a_language_leaves_out():
    """Every prompt the tasks use is defined, whichever actions a language set leaves out."""
    for language in ALL_LANGUAGES:
        tasks = document(render(language), TASKS)
        used = {
            argument
            for task in tasks["tasks"]
            for argument in task["args"]
            if "${input:" in argument
        }
        assert {f"${{input:{entry['id']}}}" for entry in tasks["inputs"]} == used


def test_the_rust_project_folders_are_linked_only_with_rust():
    linked = [
        document(render(*languages), SETTINGS).get("rust-analyzer.linkedProjects")
        for languages in ((Language.RUST,), (Language.PYTHON,))
    ]
    assert linked == [["rust/Cargo.toml", RUST_FOLDER], None]


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_either_jvm_language_gets_the_gradle_project_and_the_jvm_debug_configurations(language):
    files = render(language)
    assert {MISC, GRADLE} <= set(files)
    assert DEBUG_FOLDER in configuration_folders(files)


@pytest.mark.parametrize("language", [Language.TYPESCRIPT, Language.GO, Language.RUST])
def test_a_language_without_the_jvm_gets_no_gradle_project_files(language):
    files = render(language)
    assert {MISC, GRADLE}.isdisjoint(files)
    assert configuration_folders(files) == FOLDERS


def test_the_jvm_debug_configurations_come_with_the_jvm_languages_in_any_company():
    files = render(Language.PYTHON, Language.KOTLIN)
    assert DEBUG_FOLDER in configuration_folders(files)
    assert "Debug current file (Python)" in launch_names(files)
