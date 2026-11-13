"""The Kotlin LSP in `cstudy doctor` and `--fix` (docs/specs/cli.md#cstudy-doctor, ADR 0018,
Kotlin revisited): its row with the build's last day, the warning ahead of it and the expiry
after it; the fetch of JetBrains' newest build, checked by its published SHA-256, under the
license of its release, which you accept once; and the warm-up that fills Gradle's cache with
what it reads offline."""

from collections.abc import Callable
from dataclasses import replace
from datetime import date

from coding_study.application.doctor import CheckResult, fix_workspace
from coding_study.application.ports import NoBuild, NotInstalled, ProbeResult
from coding_study.domain.code_intelligence import KOTLIN_LSP_LICENSE, LanguageServer, License
from coding_study.domain.problem import Language
from coding_study.domain.server_builds import Build
from tests.application.test_doctor import BUNDLED, JDK_HOME, OK, WARN, FakeJdk, workspace_with
from tests.application.test_doctor_code_intelligence import OFF, code_intelligence_rows
from tests.fakes import (
    CODE_INTELLIGENCE_ON,
    INSTALLED_SERVERS,
    KOTLIN_DOWNLOADS,
    NEWEST_KOTLIN,
    FakeLanguageServers,
)

KOTLIN_ROW = "code intelligence kotlin"
FIX = "cstudy doctor --fix"
ACCEPT = "cstudy doctor --fix --accept-license kotlin-lsp"
LICENSE = "JetBrains Free Plugin License Agreement 1.0"
LICENSE_URL = "https://github.com/Kotlin/kotlin-lsp/blob/main/kotlin-vscode/LICENSE.txt"
FETCH_STEP = "fetch the newest kotlin-lsp (in .cs/lsp/kotlin-lsp)"
DOWNLOAD_STEP = (
    f"download {KOTLIN_DOWNLOADS}/263.7084.0/kotlin-server-263.7084.0-aarch64.sit "
    "(in .cs/lsp/kotlin-lsp)"
)
WARM_UP_STEP = "warm up kotlin-lsp (in jvm)"
WITHOUT_KOTLIN = {name: probe for name, probe in INSTALLED_SERVERS.items() if name != "kotlin-lsp"}
"""Every other server installed, so only the Kotlin LSP is fetched."""
NEWER = replace(
    NEWEST_KOTLIN,
    build=Build(
        "263.9000.0",
        "kotlin-lsp/v263.9000.0",
        f"{KOTLIN_DOWNLOADS}/263.9000.0/kotlin-server-263.9000.0-aarch64.sit",
        f"{KOTLIN_DOWNLOADS}/263.9000.0/kotlin-server-263.9000.0-aarch64.sit.sha256",
    ),
)
OTHER_TERMS = License("kotlin-lsp", "JetBrains Free Plugin License Agreement 2.0", LICENSE_URL, "")


class Consent:
    """Answers the question `--fix` asks before it downloads a server under a license."""

    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.asked: list[str] = []

    def __call__(self, server: LanguageServer, license: License) -> bool:
        self.asked.append(license.name)
        return self.answer


def kotlin_row(servers: FakeLanguageServers) -> CheckResult:
    return next(row for row in code_intelligence_rows(servers) if row.name == KOTLIN_ROW)


def fixed(
    servers: FakeLanguageServers,
    consent: Callable[[LanguageServer, License], bool] | None = None,
    preferences=CODE_INTELLIGENCE_ON,
    jdk: FakeJdk | None = None,
    notes: list[str] | None = None,
):
    workspace = workspace_with(preferences=preferences, language_servers=servers)
    notify = (notes if notes is not None else []).append
    return fix_workspace(
        workspace, BUNDLED, jdk or FakeJdk(), notify, consent or Consent(answer=False)
    )


def kotlin_steps(outcomes) -> list[tuple[str, bool]]:
    """The fetch, the download and the warm-up of the Kotlin LSP, as `--fix` reports them."""
    return [
        (str(o.step), o.succeeded)
        for o in outcomes
        if o.step.project == ".cs/lsp/kotlin-lsp" or str(o.step) == WARM_UP_STEP
    ]


# The row


def test_the_row_names_the_fetched_build_and_its_last_day():
    assert kotlin_row(FakeLanguageServers(INSTALLED_SERVERS)) == CheckResult(
        KOTLIN_ROW, OK, "kotlin-lsp 263.7084.0, runs until 2026-11-12"
    )


def test_the_row_warns_ahead_when_fewer_than_seven_days_are_left():
    servers = FakeLanguageServers(INSTALLED_SERVERS, today=date(2026, 11, 10))
    assert kotlin_row(servers) == CheckResult(
        KOTLIN_ROW,
        WARN,
        "kotlin-lsp 263.7084.0 runs until 2026-11-12 (3 days left), as JetBrains' early-access "
        "builds stop; cstudy doctor --fix fetches a newer one once there is",
        FIX,
    )


def test_the_row_of_an_expired_build_says_so_and_that_fix_fetches_the_newest():
    servers = FakeLanguageServers(INSTALLED_SERVERS, today=date(2026, 11, 13))
    assert kotlin_row(servers) == CheckResult(
        KOTLIN_ROW,
        WARN,
        "kotlin-lsp 263.7084.0 expired on 2026-11-13, as JetBrains' early-access builds do",
        FIX,
    )


def test_a_license_not_accepted_warns_naming_it_and_the_command_that_accepts_it():
    servers = FakeLanguageServers(INSTALLED_SERVERS, accepted=frozenset())
    assert kotlin_row(servers) == CheckResult(
        KOTLIN_ROW, WARN, f"kotlin-lsp needs you to accept the {LICENSE}", ACCEPT
    )


def test_a_build_not_fetched_yet_is_not_installed():
    assert kotlin_row(FakeLanguageServers()) == CheckResult(
        KOTLIN_ROW, WARN, "kotlin-lsp is not installed", FIX
    )


# The fetch


def test_fix_fetches_the_newest_build_and_puts_it_in_place():
    servers = FakeLanguageServers(WITHOUT_KOTLIN)
    fixed(servers)
    assert servers.installed_builds == ["263.7084.0"]


def test_fix_reports_the_fetch_then_the_download_of_the_newest_archive():
    notes: list[str] = []
    outcomes = fixed(FakeLanguageServers(WITHOUT_KOTLIN), notes=notes)
    assert (
        f"running {FETCH_STEP}" in notes,
        kotlin_steps(outcomes)[:1],
    ) == (True, [(DOWNLOAD_STEP, True)])


def test_fix_downloads_nothing_when_the_newest_build_is_in_place():
    notes: list[str] = []
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    fixed(servers, notes=notes)
    assert (servers.installed_builds, notes.count(f"running {DOWNLOAD_STEP}")) == ([], 0)


def test_fix_says_the_newest_build_is_in_place():
    notes: list[str] = []
    fixed(FakeLanguageServers(INSTALLED_SERVERS), notes=notes)
    assert "kotlin-lsp 263.7084.0 is JetBrains' newest build, and it is in place" in notes


def test_fix_fetches_a_newer_build_in_place_of_the_one_there():
    servers = FakeLanguageServers(INSTALLED_SERVERS, newest=NEWER)
    fixed(servers)
    assert servers.installed_builds == ["263.9000.0"]


def test_fix_fetches_the_newest_again_for_an_expired_build():
    servers = FakeLanguageServers(INSTALLED_SERVERS, today=date(2026, 11, 13))
    fixed(servers)
    assert servers.installed_builds == ["263.7084.0"]


def test_without_a_build_to_fetch_the_fetch_fails_with_why_and_the_manual_fix():
    servers = FakeLanguageServers(WITHOUT_KOTLIN, newest=NoBuild("no release has a checksum"))
    outcome = next(o for o in fixed(servers) if str(o.step) == FETCH_STEP)
    assert (outcome.succeeded, outcome.result, outcome.step.manual, servers.installed_builds) == (
        False,
        ProbeResult(1, "no release has a checksum\n"),
        "once online, run: cstudy doctor --fix",
        [],
    )


def test_a_failed_install_names_the_manual_fix_and_keeps_its_reason():
    servers = FakeLanguageServers(WITHOUT_KOTLIN)
    servers.install_build_result = ProbeResult(1, "SHA-256 mismatch\n")
    outcome = next(o for o in fixed(servers) if str(o.step) == DOWNLOAD_STEP)
    assert (outcome.succeeded, outcome.step.manual, outcome.result) == (
        False,
        "once online, run: cstudy doctor --fix",
        ProbeResult(1, "SHA-256 mismatch\n"),
    )


def test_fix_fetches_nothing_while_the_preference_is_off():
    notes: list[str] = []
    servers = FakeLanguageServers(WITHOUT_KOTLIN)
    fixed(servers, preferences=OFF, notes=notes)
    assert (servers.installed_builds, f"running {FETCH_STEP}" in notes) == ([], False)


# The license


def test_fix_asks_before_it_downloads_under_a_license_not_accepted():
    consent = Consent(answer=True)
    fixed(FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset()), consent)
    assert consent.asked == [LICENSE]


def test_fix_records_the_license_you_accept_and_then_downloads():
    servers = FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset())
    fixed(servers, Consent(answer=True))
    assert (servers.accepted, servers.installed_builds) == ({LICENSE}, ["263.7084.0"])


def test_fix_says_it_accepted_the_license():
    notes: list[str] = []
    fixed(FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset()), Consent(True), notes=notes)
    assert f"accepted the {LICENSE} for kotlin-lsp" in notes


def test_fix_downloads_nothing_and_records_nothing_when_you_do_not_accept():
    servers = FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset())
    fixed(servers, Consent(answer=False))
    assert (servers.accepted, servers.installed_builds, servers.warm_ups) == (set(), [], [])


def test_without_your_consent_fix_says_how_to_accept_the_license_later():
    notes: list[str] = []
    fixed(FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset()), notes=notes)
    assert (
        f"skipped kotlin-lsp: its license is not accepted; read the {LICENSE} "
        f"({LICENSE_URL}), then run {ACCEPT}"
    ) in notes


def test_a_license_you_do_not_accept_is_no_failed_step():
    outcomes = fixed(FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset()))
    assert kotlin_steps(outcomes) == []


def test_a_newer_build_under_the_same_license_never_asks_again():
    consent = Consent(answer=False)
    servers = FakeLanguageServers(INSTALLED_SERVERS, newest=NEWER)
    fixed(servers, consent)
    assert (consent.asked, servers.installed_builds) == ([], ["263.9000.0"])


def test_a_newer_build_under_another_license_asks_again_naming_it():
    consent = Consent(answer=False)
    servers = FakeLanguageServers(INSTALLED_SERVERS, newest=replace(NEWER, license=OTHER_TERMS))
    fixed(servers, consent)
    assert (consent.asked, servers.installed_builds) == ([OTHER_TERMS.name], [])


def test_fix_neither_asks_nor_fetches_while_the_preference_is_off():
    consent = Consent(answer=True)
    servers = FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset())
    fixed(servers, consent, preferences=OFF)
    assert (consent.asked, servers.installed_builds) == ([], [])


def test_the_catalog_license_is_the_one_the_fake_release_comes_under():
    assert NEWEST_KOTLIN.license is KOTLIN_LSP_LICENSE


# The warm-up


def test_fix_warms_the_kotlin_lsp_up_on_the_jvm_project_with_the_selected_jdk():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    fixed(servers)
    assert servers.warm_ups == [("kotlin-lsp", "jvm", JDK_HOME)]


def test_fix_warms_up_the_build_it_just_fetched():
    servers = FakeLanguageServers(WITHOUT_KOTLIN)
    fixed(servers)
    assert [name for name, _root, _home in servers.warm_ups] == ["kotlin-lsp"]


def test_the_warm_up_comes_after_gradle_has_warmed_the_jvm_project_up():
    notes: list[str] = []
    fixed(FakeLanguageServers(INSTALLED_SERVERS), notes=notes)
    gradle = max(index for index, line in enumerate(notes) if "./gradlew" in line)
    assert notes.index(f"running {WARM_UP_STEP}") > gradle


def test_a_failed_warm_up_names_the_manual_fix_and_keeps_its_output():
    servers = FakeLanguageServers(INSTALLED_SERVERS, warm_up=ProbeResult(1, "stopped\n"))
    outcome = next(o for o in fixed(servers) if str(o.step) == WARM_UP_STEP)
    assert (outcome.succeeded, outcome.step.manual, outcome.result) == (
        False,
        "once online, run: cstudy doctor --fix",
        ProbeResult(1, "stopped\n"),
    )


def test_no_warm_up_for_a_license_you_did_not_accept():
    servers = FakeLanguageServers(INSTALLED_SERVERS, accepted=frozenset())
    fixed(servers)
    assert servers.warm_ups == []


def test_no_warm_up_while_the_kotlin_lsp_is_not_there():
    servers = FakeLanguageServers({"kotlin-lsp": NotInstalled()}, newest=NoBuild("offline"))
    fixed(servers)
    assert servers.warm_ups == []


def test_no_warm_up_without_a_jdk_the_gradle_import_can_run_on():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    fixed(servers, jdk=FakeJdk(None))
    assert servers.warm_ups == []


def test_no_warm_up_while_the_preference_is_off():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    fixed(servers, preferences=OFF)
    assert servers.warm_ups == []


# The Linux build of a Kotlin service project's sidecar

SIDECAR_ROW = "code intelligence kotlin service projects"
LINUX_FETCH_STEP = "fetch the newest kotlin-lsp-linux (in .cs/lsp/kotlin-lsp-linux)"
WITHOUT_LINUX = {
    name: probe for name, probe in INSTALLED_SERVERS.items() if name != "kotlin-lsp-linux"
}
"""This machine's build in place, the sidecar's Linux build not fetched yet."""
KOTLIN_SERVICE = frozenset({Language.KOTLIN})


def test_without_a_kotlin_service_project_no_linux_build_is_fetched():
    servers = FakeLanguageServers(WITHOUT_LINUX)
    fixed(servers)
    assert servers.installed_builds == []


def test_once_a_kotlin_service_project_is_installed_fix_fetches_the_linux_build():
    servers = FakeLanguageServers(WITHOUT_LINUX, service_languages=KOTLIN_SERVICE)
    notes: list[str] = []
    fixed(servers, notes=notes)
    assert (servers.installed_builds, f"running {LINUX_FETCH_STEP}" in notes) == (
        ["263.7084.0"],
        True,
    )


def test_an_expired_build_is_fetched_again_for_this_machine_and_for_the_sidecar():
    """Both early-access builds stop on the same day, so `--fix` refreshes both."""
    servers = FakeLanguageServers(
        INSTALLED_SERVERS, today=date(2026, 11, 13), service_languages=KOTLIN_SERVICE
    )
    fixed(servers)
    assert servers.installed_builds == ["263.7084.0", "263.7084.0"]


def test_the_linux_build_is_not_fetched_while_the_license_is_not_accepted():
    servers = FakeLanguageServers(
        WITHOUT_LINUX, accepted=frozenset(), service_languages=KOTLIN_SERVICE
    )
    fixed(servers)
    assert servers.installed_builds == []


def test_the_linux_build_is_not_fetched_while_code_intelligence_is_off():
    servers = FakeLanguageServers(WITHOUT_LINUX, service_languages=KOTLIN_SERVICE)
    fixed(servers, preferences=OFF)
    assert servers.installed_builds == []


def sidecar_rows(servers: FakeLanguageServers) -> list[CheckResult]:
    return [row for row in code_intelligence_rows(servers) if row.name == SIDECAR_ROW]


def test_the_sidecar_build_has_a_row_once_a_kotlin_service_project_is_installed():
    servers = FakeLanguageServers(INSTALLED_SERVERS, service_languages=KOTLIN_SERVICE)
    assert sidecar_rows(servers) == [
        CheckResult(SIDECAR_ROW, OK, "kotlin-lsp-linux 263.7084.0, runs until 2026-11-12")
    ]


def test_a_sidecar_build_fetched_without_this_machines_build_of_its_version_warns_its_day_unknown():
    """Its last day is that of this machine's build of the same version, which `--fix` found none
    of: the record names no last day."""
    undated = replace(INSTALLED_SERVERS["kotlin-lsp-linux"], last_day=None)
    servers = FakeLanguageServers(
        {**INSTALLED_SERVERS, "kotlin-lsp-linux": undated}, service_languages=KOTLIN_SERVICE
    )
    assert sidecar_rows(servers) == [
        CheckResult(
            SIDECAR_ROW,
            WARN,
            "kotlin-lsp-linux 263.7084.0 runs until a day cstudy does not know, as JetBrains' "
            "early-access builds stop a few weeks after their release; cstudy doctor --fix "
            "fetches a newer one once there is",
            FIX,
        )
    ]


def test_a_sidecar_build_not_fetched_yet_warns_with_the_fix():
    servers = FakeLanguageServers(WITHOUT_LINUX, service_languages=KOTLIN_SERVICE)
    assert sidecar_rows(servers) == [
        CheckResult(SIDECAR_ROW, WARN, "kotlin-lsp-linux is not installed", FIX)
    ]


def test_without_a_kotlin_service_project_there_is_no_sidecar_row():
    assert sidecar_rows(FakeLanguageServers(INSTALLED_SERVERS)) == []
