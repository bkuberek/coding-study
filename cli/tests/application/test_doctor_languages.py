"""`cstudy doctor` and `doctor --fix` in a workspace that chose its languages
(docs/specs/cli.md#rows-by-language,
docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace)."""

import pytest

from coding_study.application.doctor import DoctorReport, repair_workspace
from coding_study.application.ports import ProbeResult
from coding_study.domain.config import Config
from coding_study.domain.errors import ConfigError
from coding_study.domain.problem import Language
from tests.application.test_doctor import (
    CHECKOUT,
    COMPLETE_WORKSPACE,
    CONFIG_CHECK,
    FAIL,
    JDK_HOME,
    LINKED_CHECK,
    OK,
    WARN,
    FakeCommands,
    FakeConfigSource,
    FakeJdk,
    FakeProjectLinks,
    FakeSetup,
    FakeTools,
    FolderCheckingRunner,
    LibrariesRunner,
    check,
    doctor,
    fix,
    healthy_runners,
    summary,
    workspace_with,
)
from tests.fakes import (
    CODE_INTELLIGENCE_ON,
    DELVE,
    INSTALLED_SERVERS,
    FakeDebugServers,
    FakeLanguageRunner,
    FakeLanguageServers,
)

PYTHON, TYPESCRIPT, JAVA, KOTLIN, GO, RUST = (
    Language.PYTHON,
    Language.TYPESCRIPT,
    Language.JAVA,
    Language.KOTLIN,
    Language.GO,
    Language.RUST,
)
ALL_SIX = "all six (none chosen; cstudy lang remove narrows them)"
FIX = "cstudy doctor --fix"
MACHINE_ROWS = {
    PYTHON: {"python", "uv"},
    TYPESCRIPT: {"node", "pnpm"},
    JAVA: {"java", "gradle"},
    KOTLIN: {"java", "gradle"},
    GO: {"go", "dlv"},
    RUST: {"rustc", "cargo", "debugserver"},
}
"""The machine's rows each language brings (docs/specs/cli.md#rows-by-language)."""
WORKSPACE_ROWS = {
    PYTHON: {
        "python/.venv",
        "python debugpy",
        "python pytest",
        "project links",
        "python/.venv location",
        "runner python",
    },
    TYPESCRIPT: {"typescript/node_modules", "runner typescript"},
    JAVA: {"jvm/gradlew", "runner java"},
    KOTLIN: {"jvm/gradlew", "runner kotlin"},
    GO: set[str](),
    RUST: set[str](),
}
"""The workspace rows each language brings (docs/specs/installation-and-workspaces.md)."""
SHARED_ROWS = {
    "docker",
    "docker leftovers",
    "config",
    "content",
    "installs",
    "workspace",
    "languages",
    "workspace files",
    "projects",
    "runner runtime",
    "progress database",
    "web ui assets",
    "web server",
}
MISSING_TOOLS = {
    "go": ("go", "version"),
    "rustc": ("rustc", "--version"),
    "cargo": ("cargo", "--version"),
}


def names(report: DoctorReport) -> set[str]:
    return {result.name for result in report.results}


def in_workspace(*languages: Language) -> DoctorReport:
    return doctor(workspace=workspace_with(languages=languages))


def without(*commands: tuple[str, ...]) -> FakeTools:
    """The healthy machine minus these tools."""
    tools = FakeTools()
    for command in commands:
        tools.outputs[command] = None
    return tools


@pytest.mark.parametrize("language", list(Language))
def test_a_workspace_of_one_language_shows_its_rows_and_the_shared_ones_only(language):
    own = MACHINE_ROWS[language] | WORKSPACE_ROWS[language]
    others = set().union(
        *(MACHINE_ROWS[other] | WORKSPACE_ROWS[other] for other in Language if other != language)
    )
    shown = names(in_workspace(language))
    assert (own <= shown, shown >= SHARED_ROWS, shown & (others - own)) == (True, True, set())


def test_a_workspace_that_chose_none_shows_every_row():
    shown = names(doctor())
    assert {"node", "pnpm", "java", "go", "rustc", "cargo", "dlv", "debugserver"} <= shown
    assert {"runner python", "runner typescript", "runner java", "runner kotlin"} <= shown
    assert "go and rust files" in shown


def test_the_runners_of_the_chosen_languages_answer_in_the_order_of_a_workspace():
    report = in_workspace(PYTHON, KOTLIN)
    rows = [r.name for r in report.results if r.name.startswith("runner ")]
    assert [row for row in rows if row != "runner runtime"] == ["runner python", "runner kotlin"]


@pytest.mark.parametrize(
    ("language", "other"), [(JAVA, "kotlin project libraries"), (KOTLIN, "java project libraries")]
)
def test_the_project_libraries_are_checked_for_the_chosen_jvm_language_only(language, other):
    runners = {
        **healthy_runners(),
        JAVA: LibrariesRunner(None),
        KOTLIN: LibrariesRunner(None),
    }
    shown = names(doctor(workspace=workspace_with(runners=runners, languages=(language,))))
    assert (f"{language} project libraries" in shown, other in shown) == (True, False)


def test_a_runner_of_a_language_that_is_not_chosen_is_never_started():
    runners = healthy_runners()
    doctor(workspace=workspace_with(runners=runners, languages=(PYTHON,)))
    typescript = runners[TYPESCRIPT]
    assert isinstance(typescript, FakeLanguageRunner)
    assert typescript.scopes == []


# The machine's toolchains


@pytest.mark.parametrize(("row", "language"), [("go", GO), ("rustc", RUST), ("cargo", RUST)])
def test_a_missing_toolchain_of_a_chosen_go_or_rust_fails(row, language):
    tools = without(MISSING_TOOLS[row])
    report = doctor(tools=tools, workspace=workspace_with(languages=(language,)))
    assert (check(report, row).status, report.passed) == (FAIL, False)


@pytest.mark.parametrize("row", ["go", "rustc", "cargo"])
def test_without_a_choice_the_go_and_rust_toolchains_stay_optional(row):
    report = doctor(tools=without(MISSING_TOOLS[row]))
    assert (check(report, row).status, report.passed) == (WARN, True)


def test_a_go_older_than_1_25_fails_when_go_is_chosen():
    tools = FakeTools()
    tools.outputs[("go", "version")] = ProbeResult(0, "go version go1.24.2 linux/amd64\n")
    result = check(doctor(tools=tools, workspace=workspace_with(languages=(GO,))), "go")
    assert (result.status, "need 1.25 or newer" in result.detail) == (FAIL, True)


def test_a_rustc_older_than_1_80_fails_when_rust_is_chosen():
    tools = FakeTools()
    tools.outputs[("rustc", "--version")] = ProbeResult(0, "rustc 1.79.0 (x 2024-06-01)\n")
    report = doctor(tools=tools, workspace=workspace_with(languages=(RUST,)))
    assert check(report, "rustc").status is FAIL


def test_the_toolchains_of_languages_that_are_not_chosen_may_be_missing():
    tools = without(
        *MISSING_TOOLS.values(),
        ("node", "--version"),
        ("pnpm", "--version"),
        ("gradle", "--version"),
    )
    assert doctor(tools=tools, workspace=workspace_with(languages=(PYTHON,))).passed is True


def test_uv_is_required_when_python_is_chosen():
    tools = without(("uv", "--version"))
    report = doctor(tools=tools, workspace=workspace_with(languages=(PYTHON,)))
    assert check(report, "uv").status is FAIL


def test_node_is_required_when_typescript_is_chosen():
    tools = without(("node", "--version"))
    report = doctor(tools=tools, workspace=workspace_with(languages=(TYPESCRIPT,)))
    assert (check(report, "node").status, report.passed) == (FAIL, False)


@pytest.mark.parametrize("language", [JAVA, KOTLIN])
def test_a_missing_jdk_fails_either_jvm_language(language):
    report = doctor(jdk=FakeJdk(None), workspace=workspace_with(languages=(language,)))
    assert check(report, "java").status is FAIL


def test_a_missing_jdk_is_no_failure_without_a_jvm_language():
    report = doctor(jdk=FakeJdk(None), workspace=workspace_with(languages=(PYTHON,)))
    assert ("java" in names(report), report.passed) == (False, True)


def test_a_missing_delve_only_warns_even_when_go_is_chosen():
    missing = FakeDebugServers(delve_server=type(DELVE)(DELVE.name, DELVE.install, None))
    report = doctor(debug_servers=missing, workspace=workspace_with(languages=(GO,)))
    assert (check(report, "dlv").status, report.passed) == (WARN, True)


# The languages row


class DefaultLang(FakeConfigSource):
    default: Language = PYTHON

    def load(self) -> Config:
        return Config(default_lang=self.default)


def default_lang(language: Language) -> DefaultLang:
    source = DefaultLang()
    source.default = language
    return source


class UnreadableConfig(FakeConfigSource):
    def load(self) -> Config:
        raise ConfigError(self.location, ("default_lang: not a language",))


def test_the_languages_row_lists_them_in_workspace_order():
    assert summary(in_workspace(PYTHON, GO), "languages") == (OK, "python, go")


def test_the_languages_row_follows_the_workspace_row():
    order = [result.name for result in in_workspace(PYTHON).results]
    assert order[order.index("workspace") + 1] == "languages"


def test_a_workspace_that_chose_none_has_all_six_and_says_how_to_narrow_them():
    assert summary(doctor(), "languages") == (OK, ALL_SIX)


def test_a_default_language_outside_the_languages_is_named_and_not_an_error():
    workspace = workspace_with(languages=(PYTHON, GO))
    report = doctor(config=default_lang(TYPESCRIPT), workspace=workspace)
    assert summary(report, "languages") == (
        OK,
        "python, go (cstudy start uses python: default_lang typescript is not one of them)",
    )


def test_a_default_language_among_the_languages_adds_nothing():
    report = doctor(config=default_lang(GO), workspace=workspace_with(languages=(PYTHON, GO)))
    assert summary(report, "languages") == (OK, "python, go")


def test_the_fallback_is_the_first_language_in_the_order_of_a_workspace():
    report = doctor(config=default_lang(PYTHON), workspace=workspace_with(languages=(KOTLIN, GO)))
    assert "cstudy start uses kotlin" in check(report, "languages").detail


def test_a_config_that_does_not_load_leaves_the_default_out_of_the_row():
    report = doctor(config=UnreadableConfig(), workspace=workspace_with(languages=(GO,)))
    assert summary(report, "languages") == (OK, "go")


def test_the_languages_row_has_no_fix():
    report = doctor(config=default_lang(RUST), workspace=workspace_with(languages=(PYTHON,)))
    assert check(report, "languages").fix is None


# The workspace's files and folders


def test_the_files_row_asks_for_the_files_of_the_chosen_languages_only():
    setup = FakeSetup()
    doctor(workspace=workspace_with(setup=setup, languages=(PYTHON, GO)))
    assert setup.asked == [(PYTHON, GO)]


def test_the_files_row_asks_for_every_file_without_a_choice():
    setup = FakeSetup()
    doctor(workspace=workspace_with(setup=setup))
    assert setup.asked == [None]


def test_a_missing_go_file_fails_the_files_row_when_go_is_chosen():
    setup = FakeSetup(missing=("go.work", "go/go.mod"))
    report = doctor(workspace=workspace_with(setup=setup, languages=(GO,)))
    result = check(report, "workspace files")
    assert (result.status, result.detail, result.fix) == (
        FAIL,
        "2 missing: go.work, go/go.mod",
        FIX,
    )


def test_a_workspace_that_chose_its_languages_has_no_go_and_rust_files_row():
    assert "go and rust files" not in names(in_workspace(PYTHON))


def test_the_projects_folder_stays_with_its_own_row_in_a_chosen_workspace():
    setup = FakeSetup(missing=("projects",))
    report = doctor(workspace=workspace_with(setup=setup, languages=(PYTHON,)))
    assert check(report, "workspace files").status is OK


@pytest.mark.parametrize("language", [JAVA, KOTLIN])
def test_a_missing_gradle_wrapper_fails_with_either_jvm_language(language):
    report = doctor(workspace=workspace_with(paths={"jvm"}, languages=(language,)))
    assert check(report, "jvm/gradlew").status is FAIL


def test_a_missing_gradle_wrapper_is_not_checked_without_a_jvm_language():
    report = doctor(workspace=workspace_with(paths={"jvm"}, languages=(PYTHON,)))
    assert "jvm/gradlew" not in names(report)


def test_the_folder_checks_of_a_language_that_is_not_chosen_are_left_out():
    runners = {**healthy_runners(), RUST: FolderCheckingRunner((CONFIG_CHECK, LINKED_CHECK))}
    report = doctor(workspace=workspace_with(runners=runners, languages=(PYTHON,)))
    assert {"rust project config", "rust linked projects"}.isdisjoint(names(report))


def test_the_folder_checks_of_a_chosen_language_run():
    runners = {**healthy_runners(), RUST: FolderCheckingRunner((CONFIG_CHECK, LINKED_CHECK))}
    report = doctor(workspace=workspace_with(runners=runners, languages=(RUST,)))
    assert {"rust project config", "rust linked projects"} <= names(report)


# Repair


def test_repair_writes_the_files_of_the_chosen_languages_only():
    setup = FakeSetup()
    repair_workspace(workspace_with(setup=setup, languages=(RUST,)), lambda _line: None)
    assert setup.asked == [(RUST,)]


def test_repair_writes_every_file_without_a_choice():
    setup = FakeSetup()
    repair_workspace(workspace_with(setup=setup), lambda _line: None)
    assert setup.asked == [None]


def test_repair_relinks_the_python_project_folders_only_with_python():
    links = FakeProjectLinks(unlinked_folders=("projects/a",))
    lines: list[str] = []
    repair_workspace(workspace_with(links=links, languages=(GO,)), lines.append)
    assert (links.relinked, lines) == ([], [])


def test_repair_relinks_the_python_project_folders_with_python():
    links = FakeProjectLinks(unlinked_folders=("projects/a",))
    lines: list[str] = []
    repair_workspace(workspace_with(links=links, languages=(PYTHON, GO)), lines.append)
    assert lines == ["relinked projects/a/.venv"]


def test_repair_leaves_the_folders_of_a_language_that_is_not_chosen_alone():
    runner = FolderCheckingRunner((), restored=("projects/x/.cargo/config.toml",))
    workspace = workspace_with(runners={**healthy_runners(), RUST: runner}, languages=(PYTHON,))
    repair_workspace(workspace, lambda _line: None)
    assert runner.repairs == 0


# The steps of --fix


def commands_run(languages: tuple[Language, ...] | None) -> list[tuple[str, ...]]:
    commands = FakeCommands()
    fix(workspace_with(paths=set(COMPLETE_WORKSPACE), commands=commands, languages=languages))
    return [command for command, _directory in commands.ran]


def test_fix_runs_uv_and_the_pytest_check_for_python_alone():
    assert [command[0] for command in commands_run((PYTHON,))] == ["uv", ".venv/bin/python"]


def test_fix_runs_pnpm_install_for_typescript_alone():
    assert commands_run((TYPESCRIPT,)) == [("pnpm", "install")]


@pytest.mark.parametrize("language", [JAVA, KOTLIN])
def test_fix_warms_gradle_up_for_either_jvm_language(language):
    commands = commands_run((language,))
    assert ({command[0] for command in commands}, len(commands)) == ({"./gradlew"}, 3)


@pytest.mark.parametrize("language", [GO, RUST])
def test_fix_has_no_toolchain_step_for_go_or_rust(language):
    assert commands_run((language,)) == []


def test_fix_runs_the_steps_of_the_chosen_languages_only():
    commands = commands_run((PYTHON, GO))
    assert ("uv", "sync") in commands
    assert ("pnpm", "install") not in commands
    assert not any(command[0] == "./gradlew" for command in commands)


def test_fix_runs_every_step_without_a_choice():
    assert {command[0] for command in commands_run(None)} == {
        "uv",
        ".venv/bin/python",
        "pnpm",
        "./gradlew",
    }


def test_fix_does_not_report_a_missing_jdk_without_java_or_kotlin():
    workspace = workspace_with(paths=set(COMPLETE_WORKSPACE), languages=(PYTHON,))
    outcomes = fix(workspace, jdk=FakeJdk(None))
    assert [outcome.skipped for outcome in outcomes] == [None]


def test_fix_reports_a_missing_jdk_with_kotlin():
    workspace = workspace_with(paths=set(COMPLETE_WORKSPACE), languages=(KOTLIN,))
    outcomes = fix(workspace, jdk=FakeJdk(None))
    assert [outcome.skipped for outcome in outcomes] == ["java is not installed or does not run"]


@pytest.mark.parametrize(("language", "installed"), [(TYPESCRIPT, True), (PYTHON, False)])
def test_fix_installs_the_typescript_runners_own_types_only_with_typescript(language, installed):
    commands = FakeCommands()
    fix(workspace_with(commands=commands, languages=(language,)), content=CHECKOUT)
    ran = [str(directory) for _command, directory in commands.ran]
    assert ("/checkout/runners/typescript" in ran) is installed


# The language servers


def servers_fixed(language: Language, servers: FakeLanguageServers) -> FakeLanguageServers:
    workspace = workspace_with(
        paths=set(COMPLETE_WORKSPACE),
        preferences=CODE_INTELLIGENCE_ON,
        language_servers=servers,
        languages=(language,),
    )
    fix(workspace)
    return servers


@pytest.mark.parametrize("language", [PYTHON, TYPESCRIPT])
def test_the_servers_pnpm_project_installs_with_a_node_language(language):
    assert servers_fixed(language, FakeLanguageServers()).installs == 1


@pytest.mark.parametrize("language", [JAVA, KOTLIN, GO, RUST])
def test_the_servers_pnpm_project_is_left_alone_without_a_node_language(language):
    assert servers_fixed(language, FakeLanguageServers()).installs == 0


def test_gopls_is_built_only_with_go():
    built = servers_fixed(GO, FakeLanguageServers()).go_installs
    other = servers_fixed(PYTHON, FakeLanguageServers()).go_installs
    assert (len(built), other) == (1, [])


def test_the_jdtls_archive_downloads_only_with_java():
    java = servers_fixed(JAVA, FakeLanguageServers()).downloads
    other = servers_fixed(PYTHON, FakeLanguageServers()).downloads
    assert (len(java), other) == (1, [])


def test_the_kotlin_lsp_is_fetched_only_with_kotlin():
    kotlin = servers_fixed(KOTLIN, FakeLanguageServers()).installed_builds
    other = servers_fixed(JAVA, FakeLanguageServers()).installed_builds
    assert (len(kotlin), other) == (1, [])


def test_the_kotlin_lsp_is_warmed_up_only_with_kotlin():
    kotlin = servers_fixed(KOTLIN, FakeLanguageServers(INSTALLED_SERVERS)).warm_ups
    java = servers_fixed(JAVA, FakeLanguageServers(INSTALLED_SERVERS)).warm_ups
    assert (kotlin, java) == ([("kotlin-lsp", "jvm", JDK_HOME)], [])


def test_the_code_intelligence_rows_are_those_of_the_chosen_languages():
    workspace = workspace_with(
        preferences=CODE_INTELLIGENCE_ON,
        language_servers=FakeLanguageServers(),
        languages=(GO,),
    )
    rows = [r.name for r in doctor(workspace=workspace).results if r.name.startswith("code ")]
    assert rows == ["code intelligence go"]


def test_the_note_about_skipped_servers_counts_the_chosen_languages_only():
    def noted(language: Language) -> bool:
        lines: list[str] = []
        workspace = workspace_with(language_servers=FakeLanguageServers(), languages=(language,))
        fix(workspace, notify=lines.append)
        return any("skipped the language servers" in line for line in lines)

    assert (noted(PYTHON), noted(RUST)) == (True, False)
