import pytest

from coding_study.application.code_intelligence import (
    ServerStatus,
    download_language_server,
    go_install_version,
    install_language_server_with_go,
    install_language_servers,
    is_unpacked,
    language_server_states,
)
from coding_study.application.ports import (
    FileMissing,
    JdkSelector,
    NotInstalled,
    ProbeResult,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.code_intelligence import BASEDPYRIGHT as BASEDPYRIGHT_SERVER
from coding_study.domain.code_intelligence import GOPLS, JDTLS, RUST_ANALYZER
from coding_study.domain.problem import Language
from tests.fakes import INSTALLED_SERVERS, FakeJdk, FakeLanguageServers, jdk_of

BASEDPYRIGHT = "basedpyright"
TYPESCRIPT = "typescript-language-server"
JDK_FIX = (
    "select a JDK 25 to 26 with JAVA_HOME, or install JDK 25: "
    "https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#jdk"
)


def states(servers: FakeLanguageServers, jdk: JdkSelector | None = None):
    found = language_server_states(servers, jdk or jdk_of(25))
    return {state.language: state for state in found}


def test_there_is_one_state_per_language_in_the_order_of_cstudy_list():
    found = language_server_states(FakeLanguageServers(), jdk_of(25))
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


def test_a_language_without_a_server_is_not_available_yet():
    state = states(FakeLanguageServers(INSTALLED_SERVERS))[Language.KOTLIN]
    assert (state.server, state.version, state.status, state.detail) == (
        None,
        None,
        ServerStatus.NOT_AVAILABLE,
        "not available yet",
    )


def test_a_language_without_a_server_has_no_idle_time_and_no_problem():
    state = states(FakeLanguageServers())[Language.KOTLIN]
    assert (state.idle_s, state.problem) == (None, None)


def test_only_languages_with_a_server_are_probed():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    language_server_states(servers, jdk_of(25))
    assert servers.probed == [BASEDPYRIGHT, TYPESCRIPT, "jdtls", "gopls", "rust-analyzer"]


# Java: JDT LS runs on the selected JDK, only when it is 25 or 26


def test_an_installed_jdtls_on_jdk_25_is_installed():
    state = states(FakeLanguageServers(INSTALLED_SERVERS))[Language.JAVA]
    assert (state.server, state.version, state.status, state.detail, state.idle_s) == (
        "jdtls",
        "1.63.0",
        ServerStatus.INSTALLED,
        "jdtls 1.63.0",
        300,
    )


def test_an_installed_jdtls_on_jdk_26_is_installed():
    state = states(FakeLanguageServers(INSTALLED_SERVERS), jdk_of(26))[Language.JAVA]
    assert state.status is ServerStatus.INSTALLED


@pytest.mark.parametrize("feature", [21, 24, 27])
def test_jdtls_on_another_jdk_needs_jdk_25_or_26(feature):
    state = states(FakeLanguageServers(INSTALLED_SERVERS), jdk_of(feature))[Language.JAVA]
    assert (state.status, state.detail) == (ServerStatus.NEEDS_JDK, "needs JDK 25 or 26")


def test_the_problem_of_jdtls_on_another_jdk_names_the_selected_one():
    state = states(FakeLanguageServers(INSTALLED_SERVERS), jdk_of(21))[Language.JAVA]
    assert (state.problem, state.fix) == ("jdtls needs JDK 25 or 26, not 21.0.1", JDK_FIX)


def test_the_problem_of_jdtls_without_a_jdk_says_none_was_found():
    state = states(FakeLanguageServers(INSTALLED_SERVERS), FakeJdk(jdk=None))[Language.JAVA]
    assert (state.status, state.problem) == (
        ServerStatus.NEEDS_JDK,
        "jdtls needs JDK 25 or 26; no JDK was found",
    )


def test_a_jdtls_that_is_not_installed_needs_the_fix_whatever_the_jdk():
    state = states(FakeLanguageServers(), jdk_of(21))[Language.JAVA]
    assert (state.status, state.detail, state.problem, state.fix) == (
        ServerStatus.NOT_INSTALLED,
        "not installed: run cstudy doctor --fix",
        "jdtls is not installed",
        "cstudy doctor --fix",
    )


def test_the_node_servers_do_not_depend_on_the_jdk():
    found = states(FakeLanguageServers(INSTALLED_SERVERS), FakeJdk(jdk=None))
    statuses = [found[language].status for language in (Language.PYTHON, Language.TYPESCRIPT)]
    assert statuses == [ServerStatus.INSTALLED, ServerStatus.INSTALLED]


def test_an_installed_server_has_no_fix():
    state = states(FakeLanguageServers(INSTALLED_SERVERS))[Language.PYTHON]
    assert state.fix is None


# downloading an archive server


def test_downloading_jdtls_fetches_its_pinned_archive():
    servers = FakeLanguageServers()
    download_language_server(servers, JDTLS)
    assert servers.downloads == [JDTLS.archive]


def test_downloading_returns_what_the_download_did():
    servers = FakeLanguageServers(download=ProbeResult(1, "SHA-256 mismatch"))
    assert download_language_server(servers, JDTLS) == ProbeResult(1, "SHA-256 mismatch")


def test_a_server_that_is_no_archive_is_never_downloaded():
    servers = FakeLanguageServers()
    assert (download_language_server(servers, BASEDPYRIGHT_SERVER), servers.downloads) == (None, [])


def test_the_pinned_build_of_jdtls_counts_as_unpacked():
    assert is_unpacked(FakeLanguageServers(INSTALLED_SERVERS), JDTLS) is True


def test_a_jdtls_of_another_build_is_not_unpacked():
    assert is_unpacked(FakeLanguageServers({"jdtls": NotInstalled()}), JDTLS) is False


def test_installing_returns_what_the_installer_ran():
    servers = FakeLanguageServers(installation=ProbeResult(1, "ERR_PNPM_FETCH\n"))
    assert install_language_servers(servers) == ProbeResult(1, "ERR_PNPM_FETCH\n")


def test_installing_without_pnpm_returns_none():
    assert install_language_servers(FakeLanguageServers(installation=None)) is None


# Go: gopls, at the version the selected Go pins


def test_an_installed_gopls_of_the_version_the_selected_go_pins_is_installed():
    state = states(FakeLanguageServers(INSTALLED_SERVERS))[Language.GO]
    assert (state.server, state.version, state.status, state.detail, state.idle_s) == (
        "gopls",
        "0.24.0",
        ServerStatus.INSTALLED,
        "gopls 0.24.0",
        60,
    )


def test_a_gopls_built_for_another_go_names_the_version_the_selected_go_pins():
    state = states(FakeLanguageServers(INSTALLED_SERVERS, go="1.26.2"))[Language.GO]
    assert (state.status, state.version, state.problem, state.fix) == (
        ServerStatus.NOT_INSTALLED,
        "0.23.0",
        "gopls 0.24.0 installed; cstudy needs 0.23.0",
        "cstudy doctor --fix",
    )


def test_a_gopls_that_is_not_installed_names_the_version_the_selected_go_pins():
    state = states(FakeLanguageServers(go="1.25.4"))[Language.GO]
    assert (state.status, state.version, state.detail, state.problem) == (
        ServerStatus.NOT_INSTALLED,
        "0.21.1",
        "not installed: run cstudy doctor --fix",
        "gopls is not installed",
    )


def test_go_install_builds_the_version_the_selected_go_pins_while_gopls_is_missing():
    assert go_install_version(FakeLanguageServers(go="1.26.0"), GOPLS) == "0.23.0"


def test_go_install_builds_again_when_another_version_is_installed():
    servers = FakeLanguageServers(INSTALLED_SERVERS, go="1.26.0")
    assert go_install_version(servers, GOPLS) == "0.23.0"


def test_go_install_has_nothing_to_build_when_the_pinned_version_is_installed():
    assert go_install_version(FakeLanguageServers(INSTALLED_SERVERS), GOPLS) is None


def test_go_install_builds_no_server_that_go_does_not_build():
    assert go_install_version(FakeLanguageServers(), RUST_ANALYZER) is None


def test_installing_with_go_runs_go_install_of_the_version():
    servers = FakeLanguageServers(go_install=ProbeResult(1, "go: requires go >= 1.27\n"))
    found = install_language_server_with_go(servers, GOPLS, "0.24.0")
    assert (found, servers.go_installs) == (
        ProbeResult(1, "go: requires go >= 1.27\n"),
        [(GOPLS.go_install, "0.24.0")],
    )


# Rust: rust-analyzer, from rustup or PATH, which cstudy never installs


def test_a_rust_analyzer_on_path_is_installed_whatever_its_version():
    state = states(FakeLanguageServers(INSTALLED_SERVERS))[Language.RUST]
    assert (state.server, state.version, state.status, state.detail) == (
        "rust-analyzer",
        "1.91.0",
        ServerStatus.INSTALLED,
        "rust-analyzer 1.91.0",
    )


def test_a_missing_rust_analyzer_is_added_with_rustup():
    state = states(FakeLanguageServers())[Language.RUST]
    assert (state.status, state.version, state.detail, state.problem, state.fix) == (
        ServerStatus.NOT_INSTALLED,
        None,
        "not installed: run rustup component add rust-analyzer",
        "rust-analyzer is not installed",
        "rustup component add rust-analyzer",
    )


def test_a_rust_analyzer_that_fails_says_why_and_how_to_add_it():
    probes = {"rust-analyzer": VersionFailed("dyld: Library not loaded")}
    state = states(FakeLanguageServers(probes))[Language.RUST]
    assert (state.status, state.detail, state.fix) == (
        ServerStatus.NOT_INSTALLED,
        "dyld: Library not loaded",
        "rustup component add rust-analyzer",
    )


def test_a_rust_analyzer_that_prints_no_version_is_not_installed():
    probes = {"rust-analyzer": VersionPrinted("rust-analyzer\n")}
    state = states(FakeLanguageServers(probes))[Language.RUST]
    assert (state.status, state.problem) == (
        ServerStatus.NOT_INSTALLED,
        "rust-analyzer printed no version",
    )
