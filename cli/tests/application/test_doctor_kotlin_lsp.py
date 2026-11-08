"""The Kotlin LSP in `cstudy doctor` and `--fix` (docs/specs/cli.md#cstudy-doctor, ADR 0018,
Kotlin revisited): its row, its license, the download of this machine's archive and the warm-up
that fills Gradle's cache with what it reads offline."""

from collections.abc import Callable
from datetime import date

from coding_study.application.doctor import CheckResult, fix_workspace
from coding_study.application.ports import Expired, NotInstalled, ProbeResult
from coding_study.domain.code_intelligence import KOTLIN_LSP, LanguageServer
from tests.application.test_doctor import BUNDLED, JDK_HOME, OK, WARN, FakeJdk, workspace_with
from tests.application.test_doctor_code_intelligence import OFF, code_intelligence_rows
from tests.fakes import CODE_INTELLIGENCE_ON, INSTALLED_SERVERS, FakeLanguageServers

KOTLIN_ROW = "code intelligence kotlin"
ACCEPT = "cstudy doctor --fix --accept-license kotlin-lsp"
LICENSE = "JetBrains Free Plugin License Agreement"
LICENSE_URL = "https://github.com/Kotlin/kotlin-lsp/blob/main/kotlin-vscode/LICENSE.txt"
DOWNLOAD_STEP = (
    "download https://download.jetbrains.com/language-server/kotlin-server/263.7084.0/"
    "kotlin-server-263.7084.0-aarch64.sit (in .cs/lsp/kotlin-lsp)"
)
WARM_UP_STEP = "warm up kotlin-lsp (in jvm)"
EXPIRY = date(2026, 11, 13)
WITHOUT_KOTLIN = {name: probe for name, probe in INSTALLED_SERVERS.items() if name != "kotlin-lsp"}
"""Every other server installed, so only the Kotlin LSP is downloaded."""


class Consent:
    """Answers the question `--fix` asks before it downloads a server with a license."""

    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.asked: list[str] = []

    def __call__(self, server: LanguageServer) -> bool:
        self.asked.append(server.name)
        return self.answer


def kotlin_row(servers: FakeLanguageServers) -> CheckResult:
    return next(row for row in code_intelligence_rows(servers) if row.name == KOTLIN_ROW)


def fixed(
    servers: FakeLanguageServers,
    consent: Callable[[LanguageServer], bool] | None = None,
    preferences=CODE_INTELLIGENCE_ON,
    jdk: FakeJdk | None = None,
    notes: list[str] | None = None,
):
    workspace = workspace_with(preferences=preferences, language_servers=servers)
    notify = (notes if notes is not None else []).append
    return fix_workspace(
        workspace, BUNDLED, jdk or FakeJdk(), notify, consent or Consent(answer=False)
    )


def kotlin_outcomes(outcomes):
    """The download and the warm-up of the Kotlin LSP."""
    return [
        o for o in outcomes if o.step.project == ".cs/lsp/kotlin-lsp" or str(o.step) == WARM_UP_STEP
    ]


def test_an_installed_kotlin_lsp_whose_license_you_accepted_is_ok():
    assert kotlin_row(FakeLanguageServers(INSTALLED_SERVERS)) == CheckResult(
        KOTLIN_ROW, OK, "kotlin-lsp 263.7084.0"
    )


def test_a_license_not_accepted_warns_naming_it_and_the_command_that_accepts_it():
    servers = FakeLanguageServers(INSTALLED_SERVERS, accepted=frozenset())
    assert kotlin_row(servers) == CheckResult(
        KOTLIN_ROW, WARN, f"kotlin-lsp needs you to accept the {LICENSE}", ACCEPT
    )


def test_fix_asks_before_it_downloads_a_server_whose_license_is_not_accepted():
    consent = Consent(answer=True)
    fixed(FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset()), consent)
    assert consent.asked == ["kotlin-lsp"]


def test_fix_records_the_license_you_accept_and_downloads_the_archive_of_this_machine():
    servers = FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset())
    fixed(servers, Consent(answer=True))
    assert (servers.accepted, servers.downloads) == (
        {"kotlin-lsp"},
        [KOTLIN_LSP.archives["darwin-arm64"]],
    )


def test_fix_says_it_accepted_the_license():
    notes: list[str] = []
    fixed(FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset()), Consent(True), notes=notes)
    assert f"accepted the {LICENSE} for kotlin-lsp" in notes


def test_fix_downloads_nothing_and_records_nothing_when_you_do_not_accept():
    servers = FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset())
    fixed(servers, Consent(answer=False))
    assert (servers.accepted, servers.downloads, servers.warm_ups) == (set(), [], [])


def test_without_your_consent_fix_says_how_to_accept_the_license_later():
    notes: list[str] = []
    fixed(FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset()), notes=notes)
    assert (
        f"skipped kotlin-lsp: its license is not accepted; read the {LICENSE} "
        f"({LICENSE_URL}), then run {ACCEPT}"
    ) in notes


def test_a_license_you_do_not_accept_is_no_failed_step():
    outcomes = fixed(FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset()))
    assert kotlin_outcomes(outcomes) == []


def test_fix_never_asks_again_for_a_license_you_accepted():
    consent = Consent(answer=False)
    servers = FakeLanguageServers(WITHOUT_KOTLIN)
    fixed(servers, consent)
    assert (consent.asked, servers.downloads) == ([], [KOTLIN_LSP.archives["darwin-arm64"]])


def test_fix_reports_the_download_as_a_step_naming_the_archive_of_this_machine():
    outcomes = fixed(FakeLanguageServers(WITHOUT_KOTLIN))
    download = [o for o in outcomes if o.step.project == ".cs/lsp/kotlin-lsp"]
    assert [(str(o.step), o.succeeded) for o in download] == [(DOWNLOAD_STEP, True)]


def test_fix_does_not_download_the_kotlin_lsp_again_once_its_build_is_unpacked():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    fixed(servers)
    assert servers.downloads == []


def test_a_failed_download_names_the_manual_fix_and_keeps_its_reason():
    servers = FakeLanguageServers(WITHOUT_KOTLIN, download=ProbeResult(1, "SHA-256 mismatch\n"))
    outcome = next(o for o in fixed(servers) if o.step.project == ".cs/lsp/kotlin-lsp")
    assert (outcome.succeeded, outcome.step.manual, outcome.result) == (
        False,
        "once online, run: cstudy doctor --fix",
        ProbeResult(1, "SHA-256 mismatch\n"),
    )


def test_a_machine_without_a_build_is_a_skipped_step():
    servers = FakeLanguageServers(WITHOUT_KOTLIN, machine="freebsd14-x64")
    outcome = next(o for o in fixed(servers) if o.step.project == ".cs/lsp/kotlin-lsp")
    assert (servers.downloads, outcome.detail) == (
        [],
        "skipped: kotlin-lsp has no build for freebsd14-x64",
    )


def test_fix_neither_asks_nor_downloads_while_the_preference_is_off():
    consent = Consent(answer=True)
    servers = FakeLanguageServers(WITHOUT_KOTLIN, accepted=frozenset())
    fixed(servers, consent, preferences=OFF)
    assert (consent.asked, servers.downloads) == ([], [])


def test_fix_warms_the_kotlin_lsp_up_on_the_jvm_project_with_the_selected_jdk():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    fixed(servers)
    assert servers.warm_ups == [("kotlin-lsp", "jvm", JDK_HOME)]


def test_fix_warms_the_kotlin_lsp_up_once_you_accept_its_license():
    servers = FakeLanguageServers(INSTALLED_SERVERS, accepted=frozenset())
    fixed(servers, Consent(answer=True))
    assert [name for name, _root, _home in servers.warm_ups] == ["kotlin-lsp"]


def test_the_warm_up_comes_after_gradle_has_warmed_the_jvm_project_up():
    notes: list[str] = []
    fixed(FakeLanguageServers(INSTALLED_SERVERS), notes=notes)
    gradle = max(index for index, line in enumerate(notes) if "./gradlew" in line)
    assert notes.index(f"running {WARM_UP_STEP}") > gradle


def test_fix_reports_the_warm_up_as_a_step_in_the_jvm_project():
    outcomes = fixed(FakeLanguageServers(INSTALLED_SERVERS))
    warm_up = [o for o in outcomes if str(o.step) == WARM_UP_STEP]
    assert [o.succeeded for o in warm_up] == [True]


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
    servers = FakeLanguageServers({"kotlin-lsp": NotInstalled()}, download=ProbeResult(1, "x"))
    fixed(servers)
    assert servers.warm_ups == []


def test_no_warm_up_without_a_jdk_the_gradle_import_can_run_on():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    fixed(servers, jdk=FakeJdk(None))
    assert servers.warm_ups == []


def test_an_expired_build_is_neither_downloaded_again_nor_warmed_up():
    servers = FakeLanguageServers({**INSTALLED_SERVERS, "kotlin-lsp": Expired(EXPIRY)})
    fixed(servers)
    assert (servers.downloads, servers.warm_ups) == ([], [])


def test_an_expired_build_never_asks_for_its_license():
    consent = Consent(answer=True)
    servers = FakeLanguageServers({"kotlin-lsp": Expired(EXPIRY)}, accepted=frozenset())
    fixed(servers, consent)
    assert (consent.asked, servers.accepted) == ([], set())


def test_an_expired_build_warns_with_the_upgrade():
    servers = FakeLanguageServers({**INSTALLED_SERVERS, "kotlin-lsp": Expired(EXPIRY)})
    assert kotlin_row(servers) == CheckResult(
        KOTLIN_ROW,
        WARN,
        "kotlin-lsp 263.7084.0 expired on 2026-11-13, as JetBrains' early-access builds do",
        "upgrade cstudy, whose next release pins a newer build",
    )


def test_no_warm_up_while_the_preference_is_off():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    fixed(servers, preferences=OFF)
    assert servers.warm_ups == []
