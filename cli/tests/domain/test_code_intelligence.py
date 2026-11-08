import hashlib
from pathlib import Path

import pytest

from coding_study.domain.code_intelligence import (
    BASEDPYRIGHT,
    JDTLS,
    JVM_WRAPPER_SHA256,
    LANGUAGE_SERVERS,
    LSP_DIRECTORY,
    LSP_INSTALL_COMMAND,
    NOT_AVAILABLE_YET,
    TYPESCRIPT_LANGUAGE_SERVER,
    Launch,
    server_for,
)
from coding_study.domain.jdk import JdkRange
from coding_study.domain.problem import Language

WORKSPACE = "/ws"
TYPESCRIPT = TYPESCRIPT_LANGUAGE_SERVER
LSP = f"{WORKSPACE}/{LSP_DIRECTORY}"
DATA = f"{LSP}/jdtls-data/jvm/1"
NODE_LAUNCH = Launch(LSP)
JAVA_LAUNCH = Launch(LSP, DATA, java="/jdk/bin/java", platform="darwin")
TEMPLATE_WRAPPER = (
    Path(__file__).parents[2]
    / "src/coding_study/adapters/workspace_template/jvm/gradle/wrapper/gradle-wrapper.jar"
)


def test_phase_two_adds_java_to_python_and_typescript():
    assert {server.language for server in LANGUAGE_SERVERS} == {
        Language.PYTHON,
        Language.TYPESCRIPT,
        Language.JAVA,
    }


@pytest.mark.parametrize("language", [Language.KOTLIN, Language.GO, Language.RUST])
def test_the_other_languages_have_no_server_yet(language):
    assert (server_for(language), NOT_AVAILABLE_YET) == (None, "not available yet")


def test_the_servers_are_pinned_to_the_versions_of_the_spec():
    assert [(server.name, server.version) for server in LANGUAGE_SERVERS] == [
        ("basedpyright", "1.40.2"),
        ("typescript-language-server", "6.0.3"),
        ("jdtls", "1.63.0"),
    ]


def test_the_language_server_runs_the_bin_script_of_the_package_with_node():
    command = BASEDPYRIGHT.command(NODE_LAUNCH)
    assert command == (
        "node",
        "/ws/.cs/lsp/node_modules/basedpyright/langserver.index.js",
        "--stdio",
    )


def test_basedpyright_prints_its_version_from_its_command_line_script():
    command = BASEDPYRIGHT.version_command(f"{WORKSPACE}/{LSP_DIRECTORY}")
    assert command == ("node", "/ws/.cs/lsp/node_modules/basedpyright/index.js", "--version")


def test_typescript_language_server_prints_its_version_from_the_server_script():
    command = TYPESCRIPT.version_command(f"{WORKSPACE}/{LSP_DIRECTORY}")
    assert command == (
        "node",
        "/ws/.cs/lsp/node_modules/typescript-language-server/lib/cli.mjs",
        "--version",
    )


@pytest.mark.parametrize(
    ("server", "output", "expected"),
    [
        (BASEDPYRIGHT, "basedpyright 1.40.2\nbased on pyright 1.40.2\n", "1.40.2"),
        (BASEDPYRIGHT, "basedpyright 1.39.0\n", "1.39.0"),
        (TYPESCRIPT, "6.0.3\n", "6.0.3"),
        (TYPESCRIPT, "no version here\n", None),
        (BASEDPYRIGHT, "", None),
    ],
)
def test_the_version_is_read_from_the_first_line_of_the_version_command(server, output, expected):
    assert server.printed_version(output) == expected


def test_python_checks_in_the_workspaces_standard_mode_without_auto_imports():
    """Under `basedpyright`, the section the server asks for, with `analysis` inside it: a key
    `basedpyright.analysis` is a section the server never asks for, so it would never be read."""
    assert BASEDPYRIGHT.settings == {
        "basedpyright": {
            "analysis": {"autoImportCompletions": False, "typeCheckingMode": "standard"}
        }
    }


def test_typescript_drives_the_workspaces_own_tsserver_offline_and_adds_no_imports():
    assert TYPESCRIPT.initialization_options(WORKSPACE) == {
        "tsserver": {"path": "/ws/typescript/node_modules/typescript/lib"},
        "disableAutomaticTypingAcquisition": True,
        "preferences": {"includeCompletionsForModuleExports": False},
    }


def test_python_needs_no_initialization_options():
    assert BASEDPYRIGHT.initialization_options(WORKSPACE) == {}


def test_the_node_servers_idle_for_sixty_seconds_and_java_for_five_minutes():
    """JDT LS takes seconds to import the Gradle build again, so a closed tab keeps it longer."""
    assert [server.idle_s for server in LANGUAGE_SERVERS] == [60, 60, 300]


def test_a_root_is_the_practice_project_of_the_language():
    assert [server.root_project for server in LANGUAGE_SERVERS] == ["python", "typescript", "jvm"]


def test_the_node_servers_need_no_jdk_and_no_data_of_their_own():
    assert [(server.jdks, server.data) for server in (BASEDPYRIGHT, TYPESCRIPT)] == [
        (None, None),
        (None, None),
    ]


# Java: Eclipse JDT LS, a pinned milestone (ADR 0018, phase 2)


def test_jdtls_is_a_pinned_milestone_checked_by_sha256():
    archive = JDTLS.archive
    assert archive is not None
    assert (archive.url, archive.sha256, archive.directory) == (
        "https://download.eclipse.org/jdtls/milestones/1.63.0/"
        "jdt-language-server-1.63.0-202610191322.tar.gz",
        "b1f2abe0b3cccb462cf64fb4a5587c7d09df60cf8be7748b152cbd89d018bdc4",
        "jdtls",
    )


def test_jdtls_counts_as_installed_by_the_core_plugin_of_its_milestone():
    assert (JDTLS.script, JDTLS.version_script) == (
        "jdtls/plugins/org.eclipse.jdt.ls.core_1.63.0.202610191322.jar",
        None,
    )


def test_jdtls_runs_on_jdk_25_or_26_only():
    assert JDTLS.jdks == JdkRange(25, 26)


def test_jdtls_runs_on_the_selected_jdk_with_its_heap_capped():
    command = JDTLS.command(JAVA_LAUNCH)
    assert (command[0], "-Xmx1g" in command) == ("/jdk/bin/java", True)


def test_jdtls_starts_from_the_launcher_of_its_milestone():
    command = JDTLS.command(JAVA_LAUNCH)
    jar = command[command.index("-jar") + 1]
    assert jar == f"{LSP}/jdtls/plugins/org.eclipse.equinox.launcher_1.8.0.v20260804-1928.jar"


def test_jdtls_keeps_its_configuration_and_workspace_in_the_sessions_data_directory():
    command = JDTLS.command(JAVA_LAUNCH)
    places = (command[command.index("-configuration") + 1], command[command.index("-data") + 1])
    assert places == (f"{DATA}/configuration", f"{DATA}/workspace")


def test_jdtls_writes_no_eclipse_files_into_the_projects():
    assert "-Djava.import.generatesMetadataFilesAtProjectRoot=false" in JDTLS.command(JAVA_LAUNCH)


@pytest.mark.parametrize(
    ("platform", "configuration"),
    [("darwin", "config_mac"), ("linux", "config_linux"), ("win32", "config_win")],
)
def test_jdtls_reads_the_shared_configuration_of_the_platform(platform, configuration):
    launch = Launch(LSP, DATA, java="/jdk/bin/java", platform=platform)
    area = f"-Dosgi.sharedConfiguration.area={LSP}/jdtls/{configuration}"
    assert area in JDTLS.command(launch)


def test_jdtls_keeps_its_gradle_cache_in_the_sessions_data_directory():
    assert JDTLS.environment(JAVA_LAUNCH) == {"XDG_CACHE_HOME": f"{DATA}/cache"}


def test_jdtls_finds_an_empty_list_of_gradle_versions_so_it_downloads_no_checksum():
    """JDT LS validates a root's Gradle wrapper against the checksums of every version its list
    names, downloading those it has not cached; an empty list leaves only the checksums it ships
    and the one the settings allow."""
    assert JDTLS.data_files == {"cache/tooling/gradle/versions.json": "[]"}


def test_the_node_servers_get_no_environment_of_their_own():
    assert BASEDPYRIGHT.environment(NODE_LAUNCH) == {}


def test_jdtls_imports_gradle_offline_and_builds_nothing():
    settings = JDTLS.initialization_options(WORKSPACE)["settings"]
    java = settings["java"]  # type: ignore[index]
    assert (
        java["import"]["gradle"]["offline"]["enabled"],  # type: ignore[index]
        java["import"]["maven"]["enabled"],  # type: ignore[index]
        java["autobuild"]["enabled"],  # type: ignore[index]
    ) == (True, False, False)


def test_jdtls_trusts_the_gradle_wrapper_cstudy_writes():
    java = JDTLS.settings["java"]
    checksums = java["imports"]["gradle"]["wrapper"]["checksums"]  # type: ignore[index]
    assert checksums == [{"sha256": JVM_WRAPPER_SHA256, "allowed": True}]


def test_the_trusted_wrapper_is_the_one_in_the_workspace_template():
    assert hashlib.sha256(TEMPLATE_WRAPPER.read_bytes()).hexdigest() == JVM_WRAPPER_SHA256


def test_jdtls_names_library_classes_by_jdt_uris_for_the_note_at_the_click():
    options = JDTLS.initialization_options(WORKSPACE)
    assert options["extendedClientCapabilities"] == {"classFileContentsSupport": True}


def test_jdtls_gets_the_settings_in_its_initialization_options_and_on_request():
    assert JDTLS.initialization_options(WORKSPACE)["settings"] == JDTLS.settings


def test_jdtls_keeps_a_data_directory_per_root_under_the_lsp_directory():
    assert JDTLS.data == "jdtls-data"


def test_jdtls_gets_the_same_client_capabilities_as_the_other_servers():
    assert JDTLS.capabilities == BASEDPYRIGHT.capabilities


def test_typescript_also_needs_the_workspaces_tsserver():
    requirement = TYPESCRIPT.requirement
    assert requirement is not None
    assert (requirement.path, requirement.missing) == (
        "typescript/node_modules/typescript/lib/tsserver.js",
        "typescript/node_modules missing",
    )


def test_python_needs_nothing_beyond_its_package():
    assert BASEDPYRIGHT.requirement is None


def test_the_install_never_runs_package_scripts_and_never_edits_the_lock():
    assert LSP_INSTALL_COMMAND == ("pnpm", "install", "--frozen-lockfile", "--ignore-scripts")


# the client capabilities of docs/specs/web-ui.md#the-broker


def test_both_servers_get_the_same_client_capabilities():
    assert BASEDPYRIGHT.capabilities == TYPESCRIPT.capabilities


def test_the_client_capabilities_are_the_ones_the_broker_implements():
    assert BASEDPYRIGHT.capabilities == {
        "general": {"positionEncodings": ["utf-16"]},
        "textDocument": {
            "synchronization": {"dynamicRegistration": False, "didSave": True},
            "publishDiagnostics": {"tagSupport": {"valueSet": [1, 2]}, "relatedInformation": False},
            "hover": {"contentFormat": ["markdown", "plaintext"]},
            "definition": {"linkSupport": True},
            "completion": {
                "contextSupport": True,
                "completionItem": {
                    "snippetSupport": False,
                    "documentationFormat": ["markdown", "plaintext"],
                    "resolveSupport": {"properties": ["documentation", "detail"]},
                    "labelDetailsSupport": True,
                },
            },
            "signatureHelp": {
                "contextSupport": True,
                "signatureInformation": {
                    "documentationFormat": ["markdown", "plaintext"],
                    "parameterInformation": {"labelOffsetSupport": True},
                    "activeParameterSupport": True,
                },
            },
            "diagnostic": {"dynamicRegistration": False, "relatedDocumentSupport": False},
        },
        "workspace": {
            "configuration": True,
            "workspaceFolders": True,
            "didChangeWatchedFiles": {"dynamicRegistration": True},
            "diagnostics": {"refreshSupport": True},
        },
        "window": {"workDoneProgress": False},
    }


def test_pull_diagnostics_are_declared_without_dynamic_registration():
    """basedpyright pulls only for a client that registers the capability dynamically, so it keeps
    publishing; a server that answers requests, such as rust-analyzer, is asked."""
    diagnostic = BASEDPYRIGHT.capabilities["textDocument"]["diagnostic"]  # type: ignore[index]
    assert diagnostic["dynamicRegistration"] is False  # type: ignore[index]


def test_completion_declares_no_snippet_support_so_an_item_never_leaves_placeholders():
    completion = BASEDPYRIGHT.capabilities["textDocument"]["completion"]  # type: ignore[index]
    assert completion["completionItem"]["snippetSupport"] is False  # type: ignore[index]
