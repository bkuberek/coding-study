"""The `.idea/` files of a workspace (docs/specs/installation-and-workspaces.md#ide-files)."""

import re
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath

import pytest

from coding_study.adapters.ide.intellij import IntellijProject
from coding_study.adapters.ide.launcher import LAUNCHER_IN_RUNTIME
from coding_study.adapters.runner_runtime import RUNTIME_DIRECTORY
from coding_study.domain.ide_actions import DEBUG_ATTACH
from coding_study.domain.layout import JVM_LANGUAGES
from tests.helpers import REPOSITORY_ROOT

MISC = ".idea/misc.xml"
GRADLE = ".idea/gradle.xml"
RUN_CONFIGURATIONS = ".idea/runConfigurations/"
PRACTICE_PLUGIN = (
    REPOSITORY_ROOT / "runners/jvm/practice-plugin/src/main/java/cs/gradle/PracticePlugin.java"
)
FILES = {file.path: file.content for file in IntellijProject().files()}
LISTENER = "Debug JVM (listen)"
"""The name `cstudy test --debug --debug-connect` asks you to start when nothing listens."""
DEBUG_CURRENT_FILE = "cstudy test --debug --debug-connect (current file, Java, Kotlin)"
DEBUG_ACTIVE_ATTEMPT = "cstudy test --debug --debug-connect (active attempt, Java, Kotlin)"


def run_configuration_files() -> dict[str, ET.Element]:
    return {
        path: ET.fromstring(content)
        for path, content in FILES.items()
        if path.startswith(RUN_CONFIGURATIONS)
    }


def configurations() -> dict[str, ET.Element]:
    found = [root.find("configuration") for root in run_configuration_files().values()]
    return {element.get("name", ""): element for element in found if element is not None}


def options(name: str) -> dict[str, str | None]:
    return {
        option.get("name", ""): option.get("value")
        for option in configurations()[name].findall("option")
    }


def project_component(path: str, name: str) -> ET.Element:
    component = ET.fromstring(FILES[path]).find(f"component[@name='{name}']")
    assert component is not None
    return component


def test_the_project_files_are_misc_gradle_and_run_configurations():
    others = {path for path in FILES if not path.startswith(RUN_CONFIGURATIONS)}
    assert others == {MISC, GRADLE}


@pytest.mark.parametrize("path", sorted(FILES))
def test_every_file_is_well_formed_xml(path):
    assert ET.fromstring(FILES[path]) is not None


@pytest.mark.parametrize("path", [MISC, GRADLE])
def test_project_files_declare_utf_8(path):
    assert FILES[path].startswith('<?xml version="1.0" encoding="UTF-8"?>\n<project version="4">')


def test_every_file_ends_with_a_newline():
    assert all(content.endswith(">\n") for content in FILES.values())


def test_rendering_twice_gives_the_same_files():
    assert IntellijProject().files() == IntellijProject().files()


def test_each_run_configuration_file_holds_one_shared_configuration():
    roots = run_configuration_files().values()
    shapes = {(root.tag, root.get("name"), len(root.findall("configuration"))) for root in roots}
    assert shapes == {("component", "ProjectRunConfigurationManager", 1)}


def test_run_configuration_files_are_named_like_intellij_names_them():
    for path, root in run_configuration_files().items():
        configuration = root.find("configuration")
        assert configuration is not None
        expected = re.sub(r"[^A-Za-z0-9_]", "_", configuration.get("name", ""))
        assert PurePosixPath(path).stem == expected


def test_every_configuration_is_in_a_cstudy_folder():
    folders = {element.get("folderName", "") for element in configurations().values()}
    assert all(folder.startswith("cstudy") for folder in folders)


def test_a_current_file_configuration_runs_the_launcher_on_the_quoted_file():
    configuration = configurations()["cstudy test (current file)"]
    assert (configuration.get("type"), options("cstudy test (current file)")) == (
        "JarApplication",
        {
            "JAR_PATH": f"$PROJECT_DIR$/{RUNTIME_DIRECTORY}/{LAUNCHER_IN_RUNTIME}",
            "PROGRAM_PARAMETERS": 'test "$FilePath$"',
            "WORKING_DIRECTORY": "$PROJECT_DIR$",
            "ALTERNATIVE_JRE_PATH_ENABLED": "false",
            "ALTERNATIVE_JRE_PATH": None,
        },
    )


def test_the_quotes_around_the_file_are_escaped_in_the_xml():
    content = FILES[f"{RUN_CONFIGURATIONS}cstudy_test__current_file_.xml"]
    assert 'value="test &quot;$FilePath$&quot;"' in content


def test_an_active_attempt_configuration_is_a_shell_command():
    configuration = configurations()["cstudy test (active attempt)"]
    assert (configuration.get("type"), options("cstudy test (active attempt)")) == (
        "ShConfigurationType",
        {
            "SCRIPT_TEXT": "cstudy test",
            "INDEPENDENT_SCRIPT_PATH": "true",
            "SCRIPT_PATH": "",
            "SCRIPT_OPTIONS": "",
            "INDEPENDENT_SCRIPT_WORKING_DIRECTORY": "true",
            "SCRIPT_WORKING_DIRECTORY": "$PROJECT_DIR$",
            "INDEPENDENT_INTERPRETER_PATH": "true",
            "INTERPRETER_PATH": "",
            "EXECUTE_IN_TERMINAL": "true",
            "EXECUTE_SCRIPT_FILE": "false",
        },
    )


def test_a_shell_command_has_an_empty_environment():
    assert configurations()["cstudy stats"].find("envs") is not None


def test_a_workspace_configuration_runs_its_command():
    assert options("cstudy doctor")["SCRIPT_TEXT"] == "cstudy doctor"


def test_done_has_a_configuration_per_outcome():
    names = [name for name in configurations() if name.startswith("cstudy done")]
    assert len(names) == 8


def test_done_names_the_outcome():
    assert options("cstudy done --gave-up (current file)")["PROGRAM_PARAMETERS"] == (
        'done --gave-up "$FilePath$"'
    )


def test_the_jvm_debugger_listens_and_restarts():
    configuration = configurations()[LISTENER]
    assert (configuration.get("type"), options(LISTENER)) == (
        "Remote",
        {
            "USE_SOCKET_TRANSPORT": "true",
            "SERVER_MODE": "true",
            "SHMEM_ADDRESS": None,
            "HOST": "localhost",
            "PORT": "5005",
            "AUTO_RESTART": "true",
        },
    )


def test_the_listener_waits_on_the_port_java_and_kotlin_connect_to():
    ports = {attach.port for attach in DEBUG_ATTACH if attach.language in JVM_LANGUAGES}
    assert ports == {int(options(LISTENER)["PORT"] or 0)}


@pytest.mark.parametrize(
    ("compound", "run", "run_type"),
    [
        ("Debug current file (Java, Kotlin)", DEBUG_CURRENT_FILE, "JarApplication"),
        ("Debug active attempt (Java, Kotlin)", DEBUG_ACTIVE_ATTEMPT, "ShConfigurationType"),
    ],
)
def test_a_debug_compound_starts_the_listener_and_cstudy(compound, run, run_type):
    parts = [
        (part.get("name"), part.get("type")) for part in configurations()[compound].findall("toRun")
    ]
    assert parts == [(LISTENER, "Remote"), (run, run_type)]


def test_every_compound_part_exists():
    known = {(name, element.get("type")) for name, element in configurations().items()}
    parts = {
        (part.get("name"), part.get("type"))
        for element in configurations().values()
        for part in element.findall("toRun")
    }
    assert parts <= known


def test_the_debug_run_connects_to_the_listener():
    parameters = options(DEBUG_CURRENT_FILE)["PROGRAM_PARAMETERS"]
    assert parameters == 'test --debug --debug-connect "$FilePath$"'


def test_python_and_typescript_have_no_intellij_debugging():
    debugging = [name for name in configurations() if "debug" in name.lower()]
    assert not [name for name in debugging if "Python" in name or "TypeScript" in name]


def test_the_project_jdk_is_the_jvm_toolchain_of_the_workspace():
    toolchain = re.search(r"JAVA_VERSION = (\d+);", PRACTICE_PLUGIN.read_text())
    assert toolchain is not None
    manager = project_component(MISC, "ProjectRootManager")
    assert (manager.get("project-jdk-name"), manager.get("languageLevel")) == (
        toolchain[1],
        f"JDK_{toolchain[1]}",
    )


def test_the_project_jdk_is_a_java_sdk():
    assert project_component(MISC, "ProjectRootManager").get("project-jdk-type") == "JavaSDK"


def test_gradle_links_the_jvm_project():
    settings = project_component(GRADLE, "GradleSettings").find("option/GradleProjectSettings")
    assert settings is not None
    values = {option.get("name"): option.get("value") for option in settings.findall("option")}
    assert (values["externalProjectPath"], values["gradleJvm"]) == (
        "$PROJECT_DIR$/jvm",
        "#USE_PROJECT_JDK",
    )


def test_gradle_lists_the_java_and_kotlin_modules():
    modules = ET.fromstring(FILES[GRADLE]).findall(".//option[@name='modules']/set/option")
    assert [module.get("value") for module in modules] == [
        "$PROJECT_DIR$/jvm",
        "$PROJECT_DIR$/jvm/java",
        "$PROJECT_DIR$/jvm/kotlin",
    ]
