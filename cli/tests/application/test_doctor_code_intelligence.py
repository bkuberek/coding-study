"""The `code intelligence` rows and the `.cs/lsp/` install of `cstudy doctor`
(docs/specs/cli.md#cstudy-doctor)."""

from coding_study.application.doctor import CheckResult, NotFound
from coding_study.application.ports import (
    FileMissing,
    NotInstalled,
    ProbeResult,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.code_intelligence import GOPLS, JDTLS
from coding_study.domain.jdk import JdkSource, SelectedJdk
from tests.application.test_doctor import (
    COMPLETE_WORKSPACE,
    OK,
    WARN,
    FakeCommands,
    FakeJdk,
    doctor,
    fix,
    workspace_with,
)
from tests.fakes import (
    CODE_INTELLIGENCE_ON,
    INSTALLED_SERVERS,
    FakeLanguageServers,
    MemoryPreferences,
)

PYTHON_ROW = "code intelligence python"
TYPESCRIPT_ROW = "code intelligence typescript"
JAVA_ROW = "code intelligence java"
GO_ROW = "code intelligence go"
RUST_ROW = "code intelligence rust"
RUSTUP_FIX = "rustup component add rust-analyzer"
GO_INSTALL_STEP = "go install golang.org/x/tools/gopls@v0.24.0 (in .cs/lsp/bin)"
JDK_25_TO_26 = (
    "select a JDK 25 to 26 with JAVA_HOME, or install JDK 25: "
    "https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#jdk"
)
DOWNLOAD_STEP = (
    "download https://download.eclipse.org/jdtls/milestones/1.63.0/"
    "jdt-language-server-1.63.0-202610191322.tar.gz (in .cs/lsp/jdtls)"
)
BASEDPYRIGHT = "basedpyright"
TYPESCRIPT = "typescript-language-server"
FIX = "cstudy doctor --fix"
INSTALL_STEP = "pnpm install --frozen-lockfile --ignore-scripts (in .cs/lsp)"
SKIPPED_NOTE = (
    "skipped the language servers: code intelligence is off; "
    "turn it on in Settings of cstudy serve, then run cstudy doctor --fix again"
)
OFF = MemoryPreferences({"format": 1, "code_intelligence": False})


def code_intelligence_rows(
    servers: FakeLanguageServers, preferences=CODE_INTELLIGENCE_ON, jdk: FakeJdk | None = None
):
    workspace = workspace_with(preferences=preferences, language_servers=servers)
    report = doctor(workspace=workspace, jdk=jdk)
    return [result for result in report.results if result.name.startswith("code intelligence")]


def java_row(servers: FakeLanguageServers, jdk: FakeJdk | None = None) -> CheckResult:
    return next(row for row in code_intelligence_rows(servers, jdk=jdk) if row.name == JAVA_ROW)


def test_the_installed_servers_report_their_pinned_versions():
    assert code_intelligence_rows(FakeLanguageServers(INSTALLED_SERVERS)) == [
        CheckResult(PYTHON_ROW, OK, "basedpyright 1.40.2"),
        CheckResult(TYPESCRIPT_ROW, OK, "typescript-language-server 6.0.3"),
        CheckResult(JAVA_ROW, OK, "jdtls 1.63.0"),
        CheckResult(GO_ROW, OK, "gopls 0.24.0"),
        CheckResult(RUST_ROW, OK, "rust-analyzer 1.91.0"),
    ]


def test_servers_that_are_not_installed_only_warn_and_name_the_fix():
    rows = code_intelligence_rows(FakeLanguageServers())
    assert rows == [
        CheckResult(PYTHON_ROW, WARN, "basedpyright is not installed", FIX),
        CheckResult(TYPESCRIPT_ROW, WARN, "typescript-language-server is not installed", FIX),
        CheckResult(JAVA_ROW, WARN, "jdtls is not installed", FIX),
        CheckResult(GO_ROW, WARN, "gopls is not installed", FIX),
        CheckResult(RUST_ROW, WARN, "rust-analyzer is not installed", RUSTUP_FIX),
    ]


def test_a_gopls_built_for_another_go_warns_with_the_version_the_selected_go_pins():
    rows = code_intelligence_rows(FakeLanguageServers(INSTALLED_SERVERS, go="1.25.4"))
    go_row = next(row for row in rows if row.name == GO_ROW)
    assert go_row == CheckResult(GO_ROW, WARN, "gopls 0.24.0 installed; cstudy needs 0.21.1", FIX)


def test_jdtls_on_a_jdk_below_25_warns_naming_the_jdk():
    jdk = FakeJdk(SelectedJdk("21.0.13", 21, JdkSource.JAVA_HOME))
    assert java_row(FakeLanguageServers(INSTALLED_SERVERS), jdk) == CheckResult(
        JAVA_ROW, WARN, "jdtls needs JDK 25 or 26, not 21.0.13", JDK_25_TO_26
    )


def test_jdtls_without_a_jdk_warns_that_none_was_found():
    row = java_row(FakeLanguageServers(INSTALLED_SERVERS), FakeJdk(None))
    assert (row.status, row.detail) == (WARN, "jdtls needs JDK 25 or 26; no JDK was found")


def test_jdtls_on_jdk_26_is_ok():
    jdk = FakeJdk(SelectedJdk("26.0.1", 26, JdkSource.JAVA_HOME))
    assert java_row(FakeLanguageServers(INSTALLED_SERVERS), jdk).status == OK


def test_warnings_for_servers_never_fail_the_report():
    workspace = workspace_with(preferences=CODE_INTELLIGENCE_ON)
    assert doctor(workspace=workspace).passed is True


def test_another_version_warns_with_both_versions():
    probes = {**INSTALLED_SERVERS, BASEDPYRIGHT: VersionPrinted("basedpyright 1.39.0\n")}
    rows = code_intelligence_rows(FakeLanguageServers(probes))
    assert rows[0] == CheckResult(
        PYTHON_ROW, WARN, "basedpyright 1.39.0 installed; cstudy needs 1.40.2", FIX
    )


def test_a_version_command_that_fails_warns_with_its_line():
    probes = {**INSTALLED_SERVERS, BASEDPYRIGHT: VersionFailed("Error: Cannot find module 'x'")}
    rows = code_intelligence_rows(FakeLanguageServers(probes))
    assert rows[0] == CheckResult(PYTHON_ROW, WARN, "Error: Cannot find module 'x'", FIX)


def test_typescript_without_the_workspaces_tsserver_warns():
    probes = {**INSTALLED_SERVERS, TYPESCRIPT: FileMissing("typescript/node_modules/x")}
    rows = code_intelligence_rows(FakeLanguageServers(probes))
    assert rows[1] == CheckResult(TYPESCRIPT_ROW, WARN, "typescript/node_modules missing", FIX)


def test_there_are_no_rows_while_the_preference_is_off():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    off = MemoryPreferences({"format": 1, "code_intelligence": False})
    assert code_intelligence_rows(servers, off) == []


def test_there_are_no_rows_without_a_preferences_file():
    assert code_intelligence_rows(FakeLanguageServers(), MemoryPreferences()) == []


def test_there_are_no_rows_when_the_preferences_file_is_invalid():
    assert code_intelligence_rows(FakeLanguageServers(), MemoryPreferences({"vim": 3})) == []


def test_a_plain_doctor_with_the_preference_off_runs_no_server():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    code_intelligence_rows(servers, MemoryPreferences({"code_intelligence": False}))
    assert servers.probed == []


def test_autocomplete_alone_does_not_turn_the_rows_on():
    only_autocomplete = MemoryPreferences({"autocomplete": True})
    assert code_intelligence_rows(FakeLanguageServers(), only_autocomplete) == []


def test_there_are_no_rows_outside_a_workspace():
    report = doctor(workspace=NotFound("no workspace here"))
    assert [r for r in report.results if r.name.startswith("code intelligence")] == []


def fix_with(
    servers: FakeLanguageServers,
    preferences=CODE_INTELLIGENCE_ON,
    jdk: FakeJdk | None = None,
    **kwargs,
):
    workspace = workspace_with(preferences=preferences, language_servers=servers, **kwargs)
    return fix(workspace, jdk=jdk)


def test_fix_downloads_jdtls_while_the_preference_is_on():
    servers = FakeLanguageServers()
    fix_with(servers)
    assert servers.downloads == [JDTLS.archive]


def test_fix_reports_the_download_as_a_step_in_its_directory():
    outcomes = fix_with(FakeLanguageServers())
    download = [outcome for outcome in outcomes if outcome.step.project == ".cs/lsp/jdtls"]
    assert [(str(outcome.step), outcome.succeeded) for outcome in download] == [
        (DOWNLOAD_STEP, True)
    ]


def test_fix_does_not_download_jdtls_again_once_its_build_is_unpacked():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    outcomes = fix_with(servers)
    reported = [outcome for outcome in outcomes if outcome.step.project == ".cs/lsp/jdtls"]
    assert (servers.downloads, reported) == ([], [])


def test_fix_downloads_jdtls_again_when_another_build_is_there():
    servers = FakeLanguageServers({**INSTALLED_SERVERS, "jdtls": NotInstalled()})
    fix_with(servers)
    assert servers.downloads == [JDTLS.archive]


def test_fix_downloads_nothing_while_the_preference_is_off():
    servers = FakeLanguageServers()
    fix_with(servers, MemoryPreferences({"code_intelligence": False}))
    assert servers.downloads == []


def test_a_failed_download_names_the_manual_fix_and_keeps_its_reason():
    servers = FakeLanguageServers(download=ProbeResult(1, "SHA-256 mismatch\n"))
    outcome = next(o for o in fix_with(servers) if o.step.project == ".cs/lsp/jdtls")
    assert (outcome.succeeded, outcome.step.manual, outcome.result) == (
        False,
        "once online, run: cstudy doctor --fix",
        ProbeResult(1, "SHA-256 mismatch\n"),
    )


def test_fix_downloads_jdtls_whatever_the_jdk_so_a_jdk_25_installed_later_needs_no_network():
    servers = FakeLanguageServers()
    fix_with(servers, jdk=FakeJdk(None))
    assert servers.downloads == [JDTLS.archive]


def test_fix_downloads_after_the_install_and_before_gradle():
    lines: list[str] = []
    workspace = workspace_with(
        preferences=CODE_INTELLIGENCE_ON, language_servers=FakeLanguageServers()
    )
    fix(workspace, notify=lines.append)
    download = lines.index(f"running {DOWNLOAD_STEP}")
    gradle = next(index for index, line in enumerate(lines) if "./gradlew" in line)
    assert lines.index(f"running {INSTALL_STEP}") < download < gradle


def test_fix_installs_the_servers_while_the_preference_is_on():
    servers = FakeLanguageServers()
    fix_with(servers)
    assert servers.installs == 1


def test_fix_reports_the_install_as_a_step_in_the_lsp_directory():
    outcomes = fix_with(FakeLanguageServers())
    install = [outcome for outcome in outcomes if outcome.step.project == ".cs/lsp"]
    assert [(str(outcome.step), outcome.succeeded) for outcome in install] == [(INSTALL_STEP, True)]


def test_fix_installs_nothing_while_the_preference_is_off():
    servers = FakeLanguageServers()
    outcomes = fix_with(servers, MemoryPreferences({"code_intelligence": False}))
    assert (servers.installs, [o for o in outcomes if o.step.project == ".cs/lsp"]) == (0, [])


def test_fix_installs_nothing_without_a_preferences_file():
    servers = FakeLanguageServers()
    fix_with(servers, MemoryPreferences())
    assert servers.installs == 0


def test_fix_runs_the_install_after_the_typescript_install_and_before_gradle():
    lines: list[str] = []
    workspace = workspace_with(
        preferences=CODE_INTELLIGENCE_ON, language_servers=FakeLanguageServers()
    )
    fix(workspace, notify=lines.append)
    steps = [line for line in lines if "(in typescript)" in line or "(in .cs/lsp)" in line]
    gradle = next(index for index, line in enumerate(lines) if "./gradlew" in line)
    assert (steps, lines.index(f"running {INSTALL_STEP}") < gradle) == (
        ["running pnpm install (in typescript)", f"running {INSTALL_STEP}"],
        True,
    )


def test_fix_still_sets_up_the_other_projects_around_the_install():
    commands = FakeCommands()
    fix_with(FakeLanguageServers(), commands=commands)
    ran = [command for command, _cwd in commands.ran]
    assert (("uv", "sync") in ran, ("pnpm", "install") in ran) == (True, True)


def test_a_failed_install_names_the_manual_fix():
    servers = FakeLanguageServers(installation=ProbeResult(1, "ERR_PNPM_FETCH_404\n"))
    outcome = next(o for o in fix_with(servers) if o.step.project == ".cs/lsp")
    assert (outcome.succeeded, outcome.step.manual, outcome.detail) == (
        False,
        "once online, run: cstudy doctor --fix",
        "exited with 1",
    )


def test_a_failed_install_keeps_its_output_for_the_last_lines():
    servers = FakeLanguageServers(installation=ProbeResult(1, "ERR_PNPM_FETCH_404\n"))
    outcome = next(o for o in fix_with(servers) if o.step.project == ".cs/lsp")
    assert outcome.result == ProbeResult(1, "ERR_PNPM_FETCH_404\n")


def test_an_install_without_pnpm_fails_that_step():
    outcome = next(
        o for o in fix_with(FakeLanguageServers(installation=None)) if o.step.project == ".cs/lsp"
    )
    assert (outcome.succeeded, outcome.detail) == (False, "pnpm not found on PATH")


def test_a_failed_install_does_not_stop_the_gradle_warm_up():
    servers = FakeLanguageServers(installation=ProbeResult(1, ""))
    commands = FakeCommands()
    fix_with(servers, commands=commands)
    assert any(command[0] == "./gradlew" for command, _cwd in commands.ran)


def test_fix_installs_into_a_workspace_without_a_typescript_project():
    servers = FakeLanguageServers()
    fix_with(servers, paths=set(COMPLETE_WORKSPACE) - {"typescript"})
    assert servers.installs == 1


def fix_notices(servers: FakeLanguageServers, preferences) -> list[str]:
    lines: list[str] = []
    fix(workspace_with(preferences=preferences, language_servers=servers), notify=lines.append)
    return [line for line in lines if "language servers" in line]


def test_fix_says_it_skipped_the_servers_while_the_preference_is_off():
    assert fix_notices(FakeLanguageServers(), OFF) == [SKIPPED_NOTE]


def test_fix_says_it_skipped_the_servers_without_a_preferences_file():
    assert fix_notices(FakeLanguageServers(), MemoryPreferences()) == [SKIPPED_NOTE]


def test_fix_still_installs_nothing_when_it_says_it_skipped_the_servers():
    servers = FakeLanguageServers()
    fix_notices(servers, OFF)
    assert servers.installs == 0


def test_fix_says_it_skipped_the_servers_when_only_one_is_installed():
    probes = {BASEDPYRIGHT: INSTALLED_SERVERS[BASEDPYRIGHT]}
    assert fix_notices(FakeLanguageServers(probes), OFF) == [SKIPPED_NOTE]


def test_fix_says_nothing_of_the_servers_that_are_already_installed():
    assert fix_notices(FakeLanguageServers(INSTALLED_SERVERS), OFF) == []


def test_fix_says_nothing_of_the_servers_while_the_preference_is_on():
    assert fix_notices(FakeLanguageServers(), CODE_INTELLIGENCE_ON) == []


def test_the_skipped_note_is_no_outcome_of_the_fix():
    outcomes = fix_with(FakeLanguageServers(), OFF)
    assert [o for o in outcomes if o.step.project == ".cs/lsp"] == []


# gopls: `go install` into `.cs/lsp/bin/`, at the version the selected Go pins


def go_outcomes(outcomes):
    return [outcome for outcome in outcomes if outcome.step.project == ".cs/lsp/bin"]


def test_fix_builds_gopls_with_go_install_while_the_preference_is_on():
    servers = FakeLanguageServers()
    fix_with(servers)
    assert servers.go_installs == [(GOPLS.go_install, "0.24.0")]


def test_fix_reports_go_install_as_a_step_in_the_lsp_bin_directory():
    outcomes = go_outcomes(fix_with(FakeLanguageServers()))
    assert [(str(outcome.step), outcome.succeeded) for outcome in outcomes] == [
        (GO_INSTALL_STEP, True)
    ]


def test_fix_builds_the_gopls_the_selected_go_pins():
    servers = FakeLanguageServers(go="1.26.0")
    fix_with(servers)
    assert servers.go_installs == [(GOPLS.go_install, "0.23.0")]


def test_fix_does_not_build_gopls_again_once_the_pinned_version_is_installed():
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    outcomes = fix_with(servers)
    assert (servers.go_installs, go_outcomes(outcomes)) == ([], [])


def test_fix_builds_gopls_again_for_a_go_that_pins_another_version():
    servers = FakeLanguageServers(INSTALLED_SERVERS, go="1.26.0")
    fix_with(servers)
    assert servers.go_installs == [(GOPLS.go_install, "0.23.0")]


def test_fix_builds_nothing_while_the_preference_is_off():
    servers = FakeLanguageServers()
    fix_with(servers, OFF)
    assert servers.go_installs == []


def test_a_failed_go_install_names_the_manual_fix_and_keeps_its_output():
    failed = ProbeResult(1, "go: golang.org/x/tools/gopls@v0.24.0: dial tcp: lookup proxy\n")
    (outcome,) = go_outcomes(fix_with(FakeLanguageServers(go_install=failed)))
    assert (outcome.succeeded, outcome.step.manual, outcome.result) == (
        False,
        "once online, run: cstudy doctor --fix",
        failed,
    )


def test_fix_without_go_fails_the_go_install_step():
    (outcome,) = go_outcomes(fix_with(FakeLanguageServers(go=None, go_install=None)))
    assert (outcome.succeeded, outcome.detail) == (False, "go not found on PATH")


def test_fix_builds_gopls_after_the_install_and_before_gradle():
    lines: list[str] = []
    workspace = workspace_with(
        preferences=CODE_INTELLIGENCE_ON, language_servers=FakeLanguageServers()
    )
    fix(workspace, notify=lines.append)
    go_install = lines.index(f"running {GO_INSTALL_STEP}")
    gradle = next(index for index, line in enumerate(lines) if "./gradlew" in line)
    assert lines.index(f"running {INSTALL_STEP}") < go_install < gradle


# rust-analyzer: the Rust toolchain's, which `--fix` never changes


RUST_NOTE = (
    "rust-analyzer is not installed: cstudy doctor --fix does not install it; "
    "run rustup component add rust-analyzer"
)


def notices_of(servers: FakeLanguageServers, preferences=CODE_INTELLIGENCE_ON) -> list[str]:
    lines: list[str] = []
    fix(workspace_with(preferences=preferences, language_servers=servers), notify=lines.append)
    return lines


def test_fix_never_installs_rust_analyzer_and_says_how_to_add_it():
    assert RUST_NOTE in notices_of(FakeLanguageServers())


def test_fix_says_nothing_of_rust_analyzer_once_it_is_on_path():
    assert RUST_NOTE not in notices_of(FakeLanguageServers(INSTALLED_SERVERS))


def test_fix_says_nothing_of_rust_analyzer_while_the_preference_is_off():
    assert RUST_NOTE not in notices_of(FakeLanguageServers(), OFF)


def test_fix_reports_no_step_for_rust_analyzer():
    outcomes = fix_with(FakeLanguageServers())
    assert [o for o in outcomes if "rust" in str(o.step)] == []


def test_a_missing_rust_analyzer_alone_is_no_reason_to_say_the_servers_were_skipped():
    probes = {**INSTALLED_SERVERS}
    del probes["rust-analyzer"]
    assert fix_notices(FakeLanguageServers(probes), OFF) == []
