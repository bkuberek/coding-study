import hashlib
from pathlib import Path

import pytest

from coding_study.domain.code_intelligence import (
    BASEDPYRIGHT,
    GOPLS,
    JDTLS,
    JVM_WRAPPER_SHA256,
    LANGUAGE_SERVERS,
    LSP_DIRECTORY,
    LSP_INSTALL_COMMAND,
    NOT_AVAILABLE_YET,
    RUST_ANALYZER,
    TYPESCRIPT_LANGUAGE_SERVER,
    Launch,
    go_release,
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


def test_every_language_has_a_server_in_cstudys_order():
    assert [server.language for server in LANGUAGE_SERVERS] == list(Language)


def test_a_language_without_a_server_would_be_not_available_yet():
    assert NOT_AVAILABLE_YET == "not available yet"


def test_the_servers_are_pinned_to_the_versions_of_the_spec():
    """gopls's is the newest the table pins; rust-analyzer is whichever runs, and the Kotlin LSP
    whichever JetBrains' newest is when `--fix` fetched it."""
    assert [(server.name, server.version) for server in LANGUAGE_SERVERS] == [
        ("basedpyright", "1.40.2"),
        ("typescript-language-server", "6.0.3"),
        ("jdtls", "1.63.0"),
        ("kotlin-lsp", None),
        ("gopls", "0.24.0"),
        ("rust-analyzer", None),
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


def test_the_servers_idle_for_sixty_seconds_and_java_and_kotlin_for_five_minutes():
    """JDT LS and the Kotlin LSP take seconds to import the Gradle build again, so a closed tab
    keeps them longer."""
    assert [server.idle_s for server in LANGUAGE_SERVERS] == [60, 60, 300, 300, 60, 60]


def test_a_root_is_the_practice_project_of_the_language():
    assert [server.root_project for server in LANGUAGE_SERVERS] == [
        "python",
        "typescript",
        "jvm",
        "jvm",
        "go",
        "rust",
    ]


def test_the_servers_but_the_jvm_ones_need_no_jdk_and_no_data_of_their_own():
    others = (BASEDPYRIGHT, TYPESCRIPT, GOPLS, RUST_ANALYZER)
    assert {(server.jdks, server.data) for server in others} == {(None, None)}


def test_cstudy_installs_every_server_but_rust_analyzer():
    assert [server.fix for server in LANGUAGE_SERVERS] == [
        None,
        None,
        None,
        None,
        None,
        "rustup component add rust-analyzer",
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


# Go: gopls, built by `go install` at the version the selected Go pins (ADR 0018, phase 3)

GO_INSTALL = GOPLS.go_install


@pytest.mark.parametrize(
    ("go", "version"),
    [
        ("1.25.4", "0.21.1"),
        ("1.26.0", "0.23.0"),
        ("1.27.3", "0.24.0"),
        ("1.28.1", "0.24.0"),
        ("1.24.9", "0.21.1"),
        (None, "0.24.0"),
    ],
    ids=["go 1.25", "go 1.26", "go 1.27", "a newer go", "an older go", "no go"],
)
def test_gopls_is_pinned_by_the_selected_go(go, version):
    """gopls v0.24.0 builds only with Go 1.27, v0.23.0 with 1.26 and v0.21.1 with 1.25."""
    assert GO_INSTALL is not None
    assert GO_INSTALL.version_for(go) == version


def test_gopls_is_built_by_go_install_at_the_pinned_version():
    assert GO_INSTALL is not None
    assert GO_INSTALL.command("0.24.0") == ("go", "install", "golang.org/x/tools/gopls@v0.24.0")


def test_go_install_puts_gopls_in_the_lsp_bin_directory_with_the_selected_go_only():
    """GOTOOLCHAIN=local never downloads another Go, and GOWORK=off keeps the workspace's
    `go.work` out of the build."""
    assert GO_INSTALL is not None
    assert GO_INSTALL.environment(LSP) == {
        "GOBIN": "/ws/.cs/lsp/bin",
        "GOTOOLCHAIN": "local",
        "GOWORK": "off",
    }


def test_only_gopls_is_built_by_go_install():
    assert [server.name for server in LANGUAGE_SERVERS if server.go_install] == ["gopls"]


def test_gopls_counts_as_installed_by_its_binary_in_the_lsp_bin_directory():
    assert GOPLS.script == "bin/gopls"


def test_gopls_prints_its_version_with_its_version_command():
    assert GOPLS.version_command(LSP) == ("/ws/.cs/lsp/bin/gopls", "version")


def test_gopls_reads_its_version_from_what_its_version_command_prints():
    assert GOPLS.printed_version("golang.org/x/tools/gopls v0.24.0\n") == "0.24.0"


def test_gopls_runs_from_the_lsp_bin_directory():
    assert GOPLS.command(NODE_LAUNCH) == ("/ws/.cs/lsp/bin/gopls",)


def test_gopls_shows_no_web_links_on_hover_and_completes_no_unimported_package():
    """Completing a package that is not imported adds its import, a quick fix out of scope."""
    settings = {"linksInHover": False, "completeUnimported": False}
    assert (GOPLS.settings, GOPLS.initialization_options(WORKSPACE)) == (
        {"gopls": settings},
        settings,
    )


def test_gopls_never_downloads_a_toolchain_or_a_module_and_builds_as_cstudy_does():
    assert GOPLS.environment(NODE_LAUNCH) == {
        "GOTOOLCHAIN": "local",
        "GOPROXY": "off",
        "GOFLAGS": "-mod=readonly",
        "CGO_ENABLED": "0",
    }


@pytest.mark.parametrize(
    ("printed", "release"),
    [
        ("go1.27.3\n", "1.27.3"),
        ("go1.26rc1\n", "1.26"),
        ("go version go1.25.4 darwin/arm64\n", "1.25.4"),
        ("", None),
        ("devel +abc\n", None),
    ],
)
def test_the_selected_go_is_read_from_what_go_prints(printed, release):
    assert go_release(printed) == release


# Rust: rust-analyzer from rustup or PATH (ADR 0018, phase 3)


def test_rust_analyzer_is_whichever_is_on_path_and_runs():
    assert (RUST_ANALYZER.script, RUST_ANALYZER.version) == (None, None)


def test_rust_analyzer_prints_its_version_with_its_version_option():
    assert RUST_ANALYZER.version_command(LSP) == ("rust-analyzer", "--version")


def test_rust_analyzer_runs_from_path():
    assert RUST_ANALYZER.command(NODE_LAUNCH) == ("rust-analyzer",)


def test_the_rustup_proxy_without_the_component_counts_as_missing():
    proxy = (
        "error: Unknown binary 'rust-analyzer' in official toolchain 'stable-aarch64-apple-darwin'."
    )
    assert RUST_ANALYZER.says_missing(proxy) is True


def test_any_other_failure_of_the_version_command_is_not_missing():
    assert RUST_ANALYZER.says_missing("dyld: Library not loaded") is False


def test_only_rust_analyzer_can_be_missing_behind_a_proxy():
    assert GOPLS.says_missing("error: Unknown binary 'gopls'") is False


def test_rust_analyzer_checks_all_targets_in_a_target_directory_of_its_own_without_imports():
    """No `--keep-going` of cstudy's: rust-analyzer passes it itself."""
    settings = {
        "cargo": {"targetDir": True},
        "check": {"allTargets": True},
        "completion": {"autoimport": {"enable": False}},
    }
    assert (RUST_ANALYZER.settings, RUST_ANALYZER.initialization_options(WORKSPACE)) == (
        {"rust-analyzer": settings},
        settings,
    )


def test_cargo_runs_offline_under_rust_analyzer():
    assert RUST_ANALYZER.environment(NODE_LAUNCH) == {"CARGO_NET_OFFLINE": "true"}


STANDARD_LIBRARY = RUST_ANALYZER.standard_library
LINKS = "/ws/.cs/lsp/rust-library/rust"


def test_rust_analyzer_reads_the_standard_library_from_links_in_the_lsp_directory():
    """The workspace's vendored crates.io reaches `cargo metadata` of the toolchain's library, so
    rust-analyzer reads the library's crates from links, without the library's manifest."""
    assert STANDARD_LIBRARY is not None
    assert (STANDARD_LIBRARY.links, STANDARD_LIBRARY.left_out) == (
        "rust-library",
        frozenset({"Cargo.toml", "Cargo.lock"}),
    )


def test_the_standard_library_is_the_rust_src_of_the_sysroot_rustc_prints():
    assert STANDARD_LIBRARY is not None
    assert (STANDARD_LIBRARY.sysroot_command, STANDARD_LIBRARY.library) == (
        ("rustc", "--print", "sysroot"),
        "lib/rustlib/src/rust/library",
    )


def test_the_links_are_rust_analyzers_sysroot_source_beside_its_other_settings():
    assert STANDARD_LIBRARY is not None
    assert STANDARD_LIBRARY.settings(RUST_ANALYZER.settings, LINKS) == {
        "rust-analyzer": {
            "cargo": {"targetDir": True, "sysrootSrc": LINKS},
            "check": {"allTargets": True},
            "completion": {"autoimport": {"enable": False}},
        }
    }


def test_the_links_leave_the_catalogs_settings_as_they_were():
    assert STANDARD_LIBRARY is not None
    STANDARD_LIBRARY.settings(RUST_ANALYZER.settings, LINKS)
    assert RUST_ANALYZER.settings == {
        "rust-analyzer": {
            "cargo": {"targetDir": True},
            "check": {"allTargets": True},
            "completion": {"autoimport": {"enable": False}},
        }
    }


def test_only_rust_analyzer_reads_the_standard_library_from_links():
    assert [server.name for server in LANGUAGE_SERVERS if server.standard_library] == [
        "rust-analyzer"
    ]


def test_go_and_rust_get_the_same_client_capabilities_as_the_other_servers():
    assert (GOPLS.capabilities, RUST_ANALYZER.capabilities) == (
        BASEDPYRIGHT.capabilities,
        BASEDPYRIGHT.capabilities,
    )
