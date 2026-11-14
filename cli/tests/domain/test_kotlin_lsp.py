"""The Kotlin LSP in the catalog (ADR 0018, Kotlin revisited): JetBrains' standalone build, pinned
per machine and checked by SHA-256, behind a license you accept."""

import shlex

import pytest

from coding_study.domain.code_intelligence import (
    CLIENT_CAPABILITIES,
    KOTLIN_LSP,
    KOTLIN_LSP_LICENSE,
    KOTLIN_LSP_LINUX,
    LANGUAGE_SERVERS,
    LSP_DIRECTORY,
    Archive,
    Launch,
    build_archive,
    machine_of,
    server_for,
)
from coding_study.domain.jdk import SUPPORTED_JDKS
from coding_study.domain.problem import Language
from coding_study.domain.server_builds import Build

LSP = f"/ws/{LSP_DIRECTORY}"
DATA = f"{LSP}/kotlin-lsp-data/jvm/1"
HOME = f"{LSP}/kotlin-lsp/server"
LAUNCH = Launch(LSP, DATA, java="/jdk/bin/java", platform="darwin", java_home="/jdk")
DOWNLOADS = "https://download.jetbrains.com/language-server/kotlin-server/263.7084.0"
SHA = "b403bf8a54bd458e3ba6731cf8abb3340be08b439c03576dfc02b13faf3694b8"
BUILD = Build(
    "263.7084.0",
    "kotlin-lsp/v263.7084.0",
    f"{DOWNLOADS}/kotlin-server-263.7084.0-aarch64.sit",
    f"{DOWNLOADS}/kotlin-server-263.7084.0-aarch64.sit.sha256",
)
TOP = "kotlin-server-263.7084.0"


def options(launch: Launch = LAUNCH) -> list[str]:
    """The JVM options the launcher reads from `IJ_JAVA_OPTIONS`, split as it splits them."""
    return shlex.split(KOTLIN_LSP.environment(launch)["IJ_JAVA_OPTIONS"])


def test_kotlin_is_served_by_the_kotlin_lsp():
    assert server_for(Language.KOTLIN) is KOTLIN_LSP


def test_the_kotlin_lsp_comes_after_java_in_the_catalog():
    languages = [server.language for server in LANGUAGE_SERVERS]
    assert languages.index(Language.KOTLIN) == languages.index(Language.JAVA) + 1


def test_cstudy_pins_no_build_of_it():
    """`cstudy doctor --fix` fetches JetBrains' newest, since each stops weeks after release."""
    assert (KOTLIN_LSP.version, KOTLIN_LSP.archive) == (None, None)


def test_it_counts_as_installed_by_the_record_fix_writes_beside_the_build():
    assert (KOTLIN_LSP.script, KOTLIN_LSP.version_script) == ("kotlin-lsp/installed.json", None)


def test_its_builds_are_the_releases_jetbrains_lists_on_github():
    releases = KOTLIN_LSP.releases
    assert releases is not None
    assert (releases.api_url, releases.license_url) == (
        "https://api.github.com/repos/Kotlin/kotlin-lsp/releases",
        "https://raw.githubusercontent.com/Kotlin/kotlin-lsp/{tag}/kotlin-vscode/LICENSE.txt",
    )


def test_a_build_is_checked_by_the_sha256_file_jetbrains_publishes_beside_it():
    releases = KOTLIN_LSP.releases
    assert releases is not None
    assert releases.checksum_suffix == ".sha256"


def test_a_build_unpacks_into_the_server_directory_from_its_top_directory():
    archive = build_archive(BUILD, SHA, "darwin-arm64")
    assert archive == Archive(BUILD.url, SHA, "kotlin-lsp", into="server", strip=TOP)


def test_a_windows_build_holds_no_top_directory_to_strip():
    archive = build_archive(BUILD, SHA, "win32-x64")
    assert (archive.into, archive.strip) == ("server", "")


@pytest.mark.parametrize(
    ("platform", "processor", "machine"),
    [
        ("darwin", "arm64", "darwin-arm64"),
        ("darwin", "x86_64", "darwin-x64"),
        ("linux", "aarch64", "linux-arm64"),
        ("linux", "x86_64", "linux-x64"),
        ("win32", "AMD64", "win32-x64"),
        ("win32", "ARM64", "win32-arm64"),
    ],
)
def test_a_machine_is_named_by_its_platform_and_processor(platform, processor, machine):
    assert machine_of(platform, processor) == machine


def test_an_unknown_processor_keeps_its_own_name():
    assert machine_of("linux", "riscv64") == "linux-riscv64"


def test_it_asks_you_to_accept_jetbrains_license_before_it_is_downloaded():
    assert KOTLIN_LSP.license is KOTLIN_LSP_LICENSE


def test_the_license_is_jetbrains_free_plugin_license_agreement_with_its_link():
    license_ = KOTLIN_LSP_LICENSE
    assert (license_.key, license_.name, license_.url) == (
        "kotlin-lsp",
        "JetBrains Free Plugin License Agreement 1.0",
        "https://github.com/Kotlin/kotlin-lsp/blob/main/kotlin-vscode/LICENSE.txt",
    )


def test_the_other_servers_need_no_license():
    others = [server for server in LANGUAGE_SERVERS if server is not KOTLIN_LSP]
    assert {server.license for server in others} == {None}


def test_it_runs_from_its_own_launcher_over_standard_streams():
    assert KOTLIN_LSP.command(LAUNCH)[:2] == (f"{HOME}/bin/intellij-server", "--stdio")


def test_on_windows_the_launcher_is_an_executable():
    windows = Launch(LSP, DATA, platform="win32")
    assert KOTLIN_LSP.command(windows)[0] == f"{HOME}/bin/intellij-server.exe"


def test_it_keeps_its_system_directory_in_the_sessions_data_directory():
    assert f"--system-path={DATA}/system" in KOTLIN_LSP.command(LAUNCH)


def test_it_keeps_its_index_and_license_store_in_the_sessions_data_directory():
    """The build keeps its index databases under `$XDG_CACHE_HOME/JetBrains/IntelliJServer/
    workspaces/`, one per root whatever the system path, and its license store in
    `$XDG_CONFIG_HOME/JetBrains/IntelliJServer`; a second session of the root needs an index of
    its own, since the first one's lock refuses it."""
    linux = Launch(LSP, DATA, java="/jdk/bin/java", platform="linux", java_home="/jdk")
    environment = KOTLIN_LSP.environment(linux)
    homes = ("XDG_CACHE_HOME", "XDG_CONFIG_HOME")

    assert {name: environment.get(name) for name in homes} == {
        "XDG_CACHE_HOME": f"{DATA}/cache",
        "XDG_CONFIG_HOME": f"{DATA}/config",
    }


@pytest.mark.parametrize("server", [KOTLIN_LSP, KOTLIN_LSP_LINUX], ids=["here", "sidecar"])
def test_it_is_told_to_keep_its_index_in_the_sessions_data_directory(server):
    """As `indexDir` in `initialize`, which the build reads on every platform, unlike the XDG
    variables: on macOS and Windows a second session of the root would otherwise find the first
    one's index in the user's cache, locked."""
    assert server.data_options(DATA) == {"indexDir": f"{DATA}/index"}


def test_its_heap_is_capped_through_the_launchers_options():
    """The launcher reads its own options file first, which asks for 2 GB, then these."""
    assert "-Xmx1g" in options()


def test_it_runs_with_the_serial_collector_and_a_smaller_code_cache():
    assert {"-XX:+UseSerialGC", "-XX:ReservedCodeCacheSize=240m"} <= set(options())


def test_it_keeps_its_configuration_logs_and_plugins_in_the_data_directory():
    assert {
        f"-Didea.config.path={DATA}/config",
        f"-Didea.log.path={DATA}/log",
        f"-Didea.plugins.path={DATA}/plugins",
    } <= set(options())


def test_it_never_checks_for_updates():
    assert "-Dintellij.updates.enabled=false" in options()


def test_it_imports_the_gradle_build_with_the_selected_jdk():
    assert "-Dcom.jetbrains.ls.imports.gradle.java.home=/jdk" in options()


def test_a_path_with_a_space_stays_one_option():
    spaced = Launch(LSP, "/my ws/data", java_home="/my jdk")
    assert "-Didea.log.path=/my ws/data/log" in options(spaced)


def test_it_needs_a_jdk_cstudy_supports_for_the_gradle_import():
    assert KOTLIN_LSP.jdks == SUPPORTED_JDKS


def test_it_keeps_a_data_directory_per_root_under_the_lsp_directory():
    assert KOTLIN_LSP.data == "kotlin-lsp-data"


def test_it_idles_five_minutes_since_a_start_imports_the_build_again():
    assert KOTLIN_LSP.idle_s == 300


def test_it_is_rooted_in_the_jvm_project():
    assert KOTLIN_LSP.root_project == "jvm"


def test_it_gets_the_same_client_capabilities_as_the_other_servers():
    assert KOTLIN_LSP.capabilities is CLIENT_CAPABILITIES


def test_cstudy_installs_it():
    assert KOTLIN_LSP.fix is None


def test_only_the_kotlin_lsp_is_fetched_at_its_newest():
    assert [server.name for server in LANGUAGE_SERVERS if server.releases] == ["kotlin-lsp"]
