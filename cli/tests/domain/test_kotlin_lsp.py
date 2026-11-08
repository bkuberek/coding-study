"""The Kotlin LSP in the catalog (ADR 0018, Kotlin revisited): JetBrains' standalone build, pinned
per machine and checked by SHA-256, behind a license you accept."""

import shlex
from datetime import date

import pytest

from coding_study.domain.code_intelligence import (
    CLIENT_CAPABILITIES,
    KOTLIN_LSP,
    KOTLIN_LSP_LICENSE,
    LANGUAGE_SERVERS,
    LSP_DIRECTORY,
    Archive,
    Launch,
    machine_of,
    server_for,
)
from coding_study.domain.jdk import SUPPORTED_JDKS
from coding_study.domain.problem import Language

LSP = f"/ws/{LSP_DIRECTORY}"
DATA = f"{LSP}/kotlin-lsp-data/jvm/1"
HOME = f"{LSP}/kotlin-lsp/kotlin-server-263.7084.0"
LAUNCH = Launch(LSP, DATA, java="/jdk/bin/java", platform="darwin", java_home="/jdk")
DOWNLOADS = "https://download.jetbrains.com/language-server/kotlin-server/263.7084.0"


def options(launch: Launch = LAUNCH) -> list[str]:
    """The JVM options the launcher reads from `IJ_JAVA_OPTIONS`, split as it splits them."""
    return shlex.split(KOTLIN_LSP.environment(launch)["IJ_JAVA_OPTIONS"])


def test_kotlin_is_served_by_the_kotlin_lsp():
    assert server_for(Language.KOTLIN) is KOTLIN_LSP


def test_the_kotlin_lsp_comes_after_java_in_the_catalog():
    languages = [server.language for server in LANGUAGE_SERVERS]
    assert languages.index(Language.KOTLIN) == languages.index(Language.JAVA) + 1


def test_it_is_pinned_to_the_measured_build():
    assert (KOTLIN_LSP.name, KOTLIN_LSP.version) == ("kotlin-lsp", "263.7084.0")


def test_it_counts_as_installed_by_a_file_whose_path_names_the_build():
    assert (KOTLIN_LSP.script, KOTLIN_LSP.version_script) == (
        "kotlin-lsp/kotlin-server-263.7084.0/build.txt",
        None,
    )


@pytest.mark.parametrize(
    ("machine", "file", "sha256"),
    [
        (
            "darwin-arm64",
            "kotlin-server-263.7084.0-aarch64.sit",
            "b403bf8a54bd458e3ba6731cf8abb3340be08b439c03576dfc02b13faf3694b8",
        ),
        (
            "darwin-x64",
            "kotlin-server-263.7084.0.sit",
            "b29c393a5e541153d03d626e7946268437e358a667a5f914a126dbb4007664b1",
        ),
        (
            "linux-x64",
            "kotlin-server-263.7084.0.tar.gz",
            "ae0c4b01e17ab73a4a5227a78ea99e6dcbe3e499600315b22759a4e4cddd11df",
        ),
        (
            "linux-arm64",
            "kotlin-server-263.7084.0-aarch64.tar.gz",
            "450ab7c1d80e48106aa429b48cb4226d82ca12a8a2400447ae02386794780cac",
        ),
    ],
)
def test_each_machine_downloads_its_own_archive_checked_by_sha256(machine, file, sha256):
    assert KOTLIN_LSP.archive_on(machine) == Archive(f"{DOWNLOADS}/{file}", sha256, "kotlin-lsp")


@pytest.mark.parametrize(
    ("machine", "file", "sha256"),
    [
        (
            "win32-x64",
            "kotlin-server-263.7084.0.win.zip",
            "be3bc4ef430cde315e6a83900ffb5d9cc454a36aabe9dd3ba7d4141b2d628164",
        ),
        (
            "win32-arm64",
            "kotlin-server-263.7084.0-aarch64.win.zip",
            "1fdf633252c098973613b69cc2e4c8ab8fe6c3e6d07241e3d424f3579745db5d",
        ),
    ],
)
def test_a_windows_archive_without_a_top_directory_is_unpacked_into_the_builds(
    machine, file, sha256
):
    expected = Archive(f"{DOWNLOADS}/{file}", sha256, "kotlin-lsp", "kotlin-server-263.7084.0")
    assert KOTLIN_LSP.archive_on(machine) == expected


def test_a_machine_jetbrains_builds_nothing_for_has_no_archive():
    assert KOTLIN_LSP.archive_on("freebsd14-x64") is None


def test_a_server_with_one_archive_has_it_on_every_machine():
    jdtls = server_for(Language.JAVA)
    assert jdtls is not None
    assert jdtls.archive_on("linux-arm64") is jdtls.archive


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
        "JetBrains Free Plugin License Agreement",
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


def test_it_keeps_its_index_and_caches_in_the_sessions_data_directory():
    assert f"--system-path={DATA}/system" in KOTLIN_LSP.command(LAUNCH)


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


def test_its_early_access_build_stops_working_on_the_day_its_license_ends():
    """`license status` named 2026-11-12 as its last day, and the build before it exits at start
    since its own day passed (`This build of kotlin-server has expired`)."""
    assert KOTLIN_LSP.expires == date(2026, 11, 13)


def test_the_other_servers_never_expire():
    others = [server for server in LANGUAGE_SERVERS if server is not KOTLIN_LSP]
    assert {server.expires for server in others} == {None}
