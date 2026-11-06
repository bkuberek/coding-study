"""The `code intelligence` rows and the `.cs/lsp/` install of `cstudy doctor`
(docs/specs/cli.md#cstudy-doctor)."""

from coding_study.application.doctor import CheckResult, NotFound
from coding_study.application.ports import (
    FileMissing,
    ProbeResult,
    VersionFailed,
    VersionPrinted,
)
from tests.application.test_doctor import (
    COMPLETE_WORKSPACE,
    OK,
    WARN,
    FakeCommands,
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
BASEDPYRIGHT = "basedpyright"
TYPESCRIPT = "typescript-language-server"
FIX = "cstudy doctor --fix"
INSTALL_STEP = "pnpm install --frozen-lockfile --ignore-scripts (in .cs/lsp)"
SKIPPED_NOTE = (
    "skipped the language servers: code intelligence is off; "
    "turn it on in Settings of cstudy serve, then run cstudy doctor --fix again"
)
OFF = MemoryPreferences({"format": 1, "code_intelligence": False})


def code_intelligence_rows(servers: FakeLanguageServers, preferences=CODE_INTELLIGENCE_ON):
    workspace = workspace_with(preferences=preferences, language_servers=servers)
    report = doctor(workspace=workspace)
    return [result for result in report.results if result.name.startswith("code intelligence")]


def test_both_servers_installed_report_their_pinned_versions():
    assert code_intelligence_rows(FakeLanguageServers(INSTALLED_SERVERS)) == [
        CheckResult(PYTHON_ROW, OK, "basedpyright 1.40.2"),
        CheckResult(TYPESCRIPT_ROW, OK, "typescript-language-server 6.0.3"),
    ]


def test_servers_that_are_not_installed_only_warn_and_name_the_fix():
    rows = code_intelligence_rows(FakeLanguageServers())
    assert rows == [
        CheckResult(PYTHON_ROW, WARN, "basedpyright is not installed", FIX),
        CheckResult(TYPESCRIPT_ROW, WARN, "typescript-language-server is not installed", FIX),
    ]


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


def fix_with(servers: FakeLanguageServers, preferences=CODE_INTELLIGENCE_ON, **kwargs):
    workspace = workspace_with(preferences=preferences, language_servers=servers, **kwargs)
    return fix(workspace)


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
    steps = [line for line in lines if "(in typescript)" in line or ".cs/lsp" in line]
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
