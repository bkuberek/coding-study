"""`GET /api/v1/code-intelligence/languages` (docs/specs/web-ui.md#code-intelligence)."""

from coding_study.application.ports import VersionFailed
from tests.fakes import INSTALLED_SERVERS, FakeJdk, FakeLanguageServers, jdk_of
from tests.web_server import anonymous_client, session_client, web_app, web_workspace

LANGUAGES = "/api/v1/code-intelligence/languages"


def languages(tmp_path, servers: FakeLanguageServers, jdk: FakeJdk | None = None):
    environment = web_workspace(tmp_path, language_servers=servers, jdk=jdk or jdk_of(25))
    with session_client(web_app(tmp_path, environment)) as client:
        return client.get(LANGUAGES)


def java_entry(tmp_path, jdk: FakeJdk) -> dict[str, object]:
    entries = languages(tmp_path, FakeLanguageServers(INSTALLED_SERVERS), jdk).json()["languages"]
    return next(entry for entry in entries if entry["language"] == "java")


def test_installed_servers_are_listed_in_the_order_of_cstudy_list(tmp_path):
    document = languages(tmp_path, FakeLanguageServers(INSTALLED_SERVERS)).json()
    assert [entry["language"] for entry in document["languages"]] == [
        "python",
        "typescript",
        "java",
        "kotlin",
        "go",
        "rust",
    ]


def test_an_installed_server_names_its_pinned_version_and_idle_time(tmp_path):
    entry = languages(tmp_path, FakeLanguageServers(INSTALLED_SERVERS)).json()["languages"][0]
    assert entry == {
        "language": "python",
        "server": "basedpyright",
        "version": "1.40.2",
        "state": "installed",
        "detail": "basedpyright 1.40.2",
        "idle_s": 60,
    }


def test_a_server_that_is_not_installed_says_how_to_install_it(tmp_path):
    entry = languages(tmp_path, FakeLanguageServers()).json()["languages"][1]
    assert entry == {
        "language": "typescript",
        "server": "typescript-language-server",
        "version": "6.0.3",
        "state": "not_installed",
        "detail": "not installed: run cstudy doctor --fix",
        "idle_s": 60,
    }


def test_a_version_command_that_fails_gives_its_own_line(tmp_path):
    servers = FakeLanguageServers({"basedpyright": VersionFailed("Error: no module")})
    entry = languages(tmp_path, servers).json()["languages"][0]
    assert (entry["state"], entry["detail"]) == ("not_installed", "Error: no module")


def test_an_installed_jdtls_on_jdk_25_is_installed(tmp_path):
    assert java_entry(tmp_path, jdk_of(25)) == {
        "language": "java",
        "server": "jdtls",
        "version": "1.63.0",
        "state": "installed",
        "detail": "jdtls 1.63.0",
        "idle_s": 300,
    }


def test_jdtls_on_another_jdk_needs_jdk_25_or_26(tmp_path):
    entry = java_entry(tmp_path, jdk_of(21))
    assert (entry["state"], entry["detail"]) == ("needs_jdk", "needs JDK 25 or 26")


def entry_of(tmp_path, servers: FakeLanguageServers, language: str) -> dict[str, object]:
    entries = languages(tmp_path, servers).json()["languages"]
    return next(entry for entry in entries if entry["language"] == language)


def test_an_installed_kotlin_lsp_whose_license_you_accepted_is_installed(tmp_path):
    entry = entry_of(tmp_path, FakeLanguageServers(INSTALLED_SERVERS), "kotlin")
    assert (entry["server"], entry["state"], entry["detail"], entry["idle_s"]) == (
        "kotlin-lsp",
        "installed",
        "kotlin-lsp 263.7084.0, runs until 2026-11-12",
        300,
    )


def test_a_kotlin_lsp_whose_license_is_not_accepted_says_so_with_the_command(tmp_path):
    servers = FakeLanguageServers(INSTALLED_SERVERS, accepted=frozenset())
    entry = entry_of(tmp_path, servers, "kotlin")
    assert (entry["state"], entry["detail"]) == (
        "license_not_accepted",
        "license not accepted: run cstudy doctor --fix --accept-license kotlin-lsp",
    )


def test_an_installed_gopls_names_the_version_the_selected_go_pins(tmp_path):
    assert entry_of(tmp_path, FakeLanguageServers(INSTALLED_SERVERS), "go") == {
        "language": "go",
        "server": "gopls",
        "version": "0.24.0",
        "state": "installed",
        "detail": "gopls 0.24.0",
        "idle_s": 60,
    }


def test_a_rust_analyzer_on_path_names_the_version_it_prints(tmp_path):
    assert entry_of(tmp_path, FakeLanguageServers(INSTALLED_SERVERS), "rust") == {
        "language": "rust",
        "server": "rust-analyzer",
        "version": "1.91.0",
        "state": "installed",
        "detail": "rust-analyzer 1.91.0",
        "idle_s": 60,
    }


def test_a_missing_rust_analyzer_says_how_to_add_it_with_no_version(tmp_path):
    assert entry_of(tmp_path, FakeLanguageServers(), "rust") == {
        "language": "rust",
        "server": "rust-analyzer",
        "version": None,
        "state": "not_installed",
        "detail": "not installed: run rustup component add rust-analyzer",
        "idle_s": 60,
    }


def test_the_list_does_not_depend_on_the_preference(tmp_path):
    """The Settings view lists each language's state whatever the checkbox says."""
    response = languages(tmp_path, FakeLanguageServers(INSTALLED_SERVERS))
    assert (response.status_code, response.json()["languages"][0]["state"]) == (200, "installed")


def test_the_list_needs_the_session_cookie(tmp_path):
    app = web_app(tmp_path)
    with anonymous_client(app) as client:
        assert client.get(LANGUAGES).status_code == 401


def test_the_list_is_not_cached(tmp_path):
    response = languages(tmp_path, FakeLanguageServers())
    assert response.headers["cache-control"] == "no-store"
