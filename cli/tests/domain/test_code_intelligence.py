import pytest

from coding_study.domain.code_intelligence import (
    BASEDPYRIGHT,
    LANGUAGE_SERVERS,
    LSP_DIRECTORY,
    LSP_INSTALL_COMMAND,
    NOT_AVAILABLE_YET,
    TYPESCRIPT_LANGUAGE_SERVER,
    server_for,
)
from coding_study.domain.problem import Language

WORKSPACE = "/ws"
TYPESCRIPT = TYPESCRIPT_LANGUAGE_SERVER


def test_slice_one_has_python_and_typescript_servers_only():
    assert {server.language for server in LANGUAGE_SERVERS} == {
        Language.PYTHON,
        Language.TYPESCRIPT,
    }


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN, Language.GO, Language.RUST])
def test_the_other_languages_have_no_server_yet(language):
    assert (server_for(language), NOT_AVAILABLE_YET) == (None, "not available yet")


def test_the_servers_are_pinned_to_the_versions_of_the_spec():
    assert [(server.name, server.version) for server in LANGUAGE_SERVERS] == [
        ("basedpyright", "1.40.2"),
        ("typescript-language-server", "6.0.3"),
    ]


def test_the_language_server_runs_the_bin_script_of_the_package_with_node():
    command = BASEDPYRIGHT.command(f"{WORKSPACE}/{LSP_DIRECTORY}")
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
    assert BASEDPYRIGHT.settings == {
        "basedpyright.analysis": {"autoImportCompletions": False, "typeCheckingMode": "standard"}
    }


def test_typescript_drives_the_workspaces_own_tsserver_offline_and_adds_no_imports():
    assert TYPESCRIPT.initialization_options(WORKSPACE) == {
        "tsserver": {"path": "/ws/typescript/node_modules/typescript/lib"},
        "disableAutomaticTypingAcquisition": True,
        "preferences": {"includeCompletionsForModuleExports": False},
    }


def test_python_needs_no_initialization_options():
    assert BASEDPYRIGHT.initialization_options(WORKSPACE) == {}


def test_both_servers_idle_for_sixty_seconds():
    assert [server.idle_s for server in LANGUAGE_SERVERS] == [60, 60]


def test_a_root_is_the_practice_project_of_the_language():
    assert [server.root_project for server in LANGUAGE_SERVERS] == ["python", "typescript"]


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
