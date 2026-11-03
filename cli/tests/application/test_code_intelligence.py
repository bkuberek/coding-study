import pytest

from coding_study.application.code_intelligence import (
    ServerStatus,
    install_language_servers,
    language_server_states,
)
from coding_study.application.ports import (
    FileMissing,
    ProbeResult,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.problem import Language
from tests.fakes import INSTALLED_SERVERS, FakeLanguageServers

BASEDPYRIGHT = "basedpyright"
TYPESCRIPT = "typescript-language-server"


def states(servers: FakeLanguageServers):
    return {state.language: state for state in language_server_states(servers)}


def test_there_is_one_state_per_language_in_the_order_of_cstudy_list():
    found = language_server_states(FakeLanguageServers())
    assert [state.language for state in found] == list(Language)


def test_an_installed_python_server_says_the_version_it_prints():
    state = states(FakeLanguageServers(INSTALLED_SERVERS))[Language.PYTHON]
    assert (state.server, state.version, state.status, state.detail, state.idle_s) == (
        BASEDPYRIGHT,
        "1.40.2",
        ServerStatus.INSTALLED,
        "basedpyright 1.40.2",
        60,
    )


def test_an_installed_typescript_server_names_its_package():
    state = states(FakeLanguageServers(INSTALLED_SERVERS))[Language.TYPESCRIPT]
    assert (state.server, state.version, state.status, state.detail) == (
        TYPESCRIPT,
        "6.0.3",
        ServerStatus.INSTALLED,
        "typescript-language-server 6.0.3",
    )


def test_installed_servers_have_no_problem():
    found = states(FakeLanguageServers(INSTALLED_SERVERS))
    assert [found[Language.PYTHON].problem, found[Language.TYPESCRIPT].problem] == [None, None]


def test_a_server_that_is_not_in_the_directory_is_not_installed():
    state = states(FakeLanguageServers())[Language.PYTHON]
    assert (state.status, state.detail, state.problem) == (
        ServerStatus.NOT_INSTALLED,
        "not installed: run cstudy doctor --fix",
        "basedpyright is not installed",
    )


def test_a_not_installed_server_still_names_the_pinned_version_and_idle_time():
    state = states(FakeLanguageServers())[Language.PYTHON]
    assert (state.server, state.version, state.idle_s) == (BASEDPYRIGHT, "1.40.2", 60)


def test_another_version_is_not_installed_and_names_both():
    probes = {BASEDPYRIGHT: VersionPrinted("basedpyright 1.39.0\n")}
    state = states(FakeLanguageServers(probes))[Language.PYTHON]
    assert (state.status, state.detail, state.problem) == (
        ServerStatus.NOT_INSTALLED,
        "basedpyright 1.39.0 installed; cstudy needs 1.40.2: run cstudy doctor --fix",
        "basedpyright 1.39.0 installed; cstudy needs 1.40.2",
    )


def test_a_version_command_that_prints_no_version_is_not_installed():
    probes = {BASEDPYRIGHT: VersionPrinted("hello\n")}
    state = states(FakeLanguageServers(probes))[Language.PYTHON]
    assert (state.status, state.problem) == (
        ServerStatus.NOT_INSTALLED,
        "basedpyright printed no version",
    )


def test_a_version_command_that_fails_gives_its_own_line():
    probes = {TYPESCRIPT: VersionFailed("Error: Cannot find module 'vscode-jsonrpc'")}
    state = states(FakeLanguageServers(probes))[Language.TYPESCRIPT]
    assert (state.status, state.detail, state.problem) == (
        ServerStatus.NOT_INSTALLED,
        "Error: Cannot find module 'vscode-jsonrpc'",
        "Error: Cannot find module 'vscode-jsonrpc'",
    )


def test_typescript_without_the_workspaces_tsserver_names_the_missing_modules():
    probes = {TYPESCRIPT: FileMissing("typescript/node_modules/typescript/lib/tsserver.js")}
    state = states(FakeLanguageServers(probes))[Language.TYPESCRIPT]
    assert (state.status, state.detail, state.problem) == (
        ServerStatus.NOT_INSTALLED,
        "typescript/node_modules missing: run cstudy doctor --fix",
        "typescript/node_modules missing",
    )


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN, Language.GO, Language.RUST])
def test_a_language_without_a_server_is_not_available_yet(language):
    state = states(FakeLanguageServers(INSTALLED_SERVERS))[language]
    assert (state.server, state.version, state.status, state.detail) == (
        None,
        None,
        ServerStatus.NOT_AVAILABLE,
        "not available yet",
    )


def test_a_language_without_a_server_has_no_idle_time_and_no_problem():
    state = states(FakeLanguageServers())[Language.GO]
    assert (state.idle_s, state.problem) == (None, None)


def test_only_languages_with_a_server_are_probed():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    language_server_states(servers)
    assert servers.probed == [BASEDPYRIGHT, TYPESCRIPT]


def test_installing_returns_what_the_installer_ran():
    servers = FakeLanguageServers(installation=ProbeResult(1, "ERR_PNPM_FETCH\n"))
    assert install_language_servers(servers) == ProbeResult(1, "ERR_PNPM_FETCH\n")


def test_installing_without_pnpm_returns_none():
    assert install_language_servers(FakeLanguageServers(installation=None)) is None
