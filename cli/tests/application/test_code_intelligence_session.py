"""Which server and root a code-intelligence session gets from an attempt
(docs/specs/web-ui.md#sessions, docs/specs/web-ui.md#language-servers)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.code_intelligence import (
    LanguageServerState,
    ServerStatus,
    SessionTarget,
    session_server_states,
    session_target,
)
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    FileMissing,
    ServerProbe,
    StubGenerator,
    VersionFailed,
    VersionPrinted,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.code_intelligence import LanguageServer
from coding_study.domain.errors import (
    AttemptEndedError,
    LanguageServerNotInstalledError,
    UnknownAttemptError,
    UsageError,
)
from coding_study.domain.preferences import Preferences
from coding_study.domain.problem import Language
from coding_study.domain.sandbox import SandboxUser, SidecarPlan, StackKind, workspace_digest
from tests.fakes import (
    INSTALLED_SERVERS,
    JDK_HOME,
    FakeLanguageServers,
    FakeStubGenerator,
    FakeToolchains,
    jdk_of,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    GRADLE_IMAGE,
    java_meta_document,
    make_content,
    meta_document,
    write_problem,
)
from tests.service_problems import SLUG as SERVICE_SLUG

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
ON = Preferences(code_intelligence=True)
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}


@pytest.fixture
def practice(tmp_path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    return make_environment(
        root,
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=FakeLanguageServers(INSTALLED_SERVERS),
    )


def started(environment: Environment, language: Language) -> Attempt:
    return start_attempt(environment, StartRequest("two-sum", language)).attempt


def target(environment: Environment, attempt: Attempt, preferences: Preferences = ON):
    return session_target(environment, preferences, attempt.id)


def test_a_python_attempt_gets_basedpyright_rooted_in_the_practice_project(practice):
    found = target(practice, started(practice, Language.PYTHON))
    assert (found.server.name, found.root, found.workspace) == (
        "basedpyright",
        "python",
        practice.root,
    )


def test_a_typescript_attempt_gets_its_language_server_rooted_in_the_practice_project(practice):
    found = target(practice, started(practice, Language.TYPESCRIPT))
    assert (found.server.name, found.root) == ("typescript-language-server", "typescript")


def java_practice(tmp_path, feature: int) -> Environment:
    return make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=FakeLanguageServers(INSTALLED_SERVERS),
        jdk=jdk_of(feature),
    )


def test_a_java_attempt_gets_jdtls_rooted_in_the_jvm_project(tmp_path):
    environment = java_practice(tmp_path, 25)
    found = target(environment, started(environment, Language.JAVA))
    assert (found.server.name, found.root) == ("jdtls", "jvm")


def test_a_java_session_runs_on_the_selected_jdk(tmp_path):
    environment = java_practice(tmp_path, 26)
    assert target(environment, started(environment, Language.JAVA)).java_home == JDK_HOME


def test_a_java_attempt_on_a_jdk_jdtls_cannot_run_on_is_refused_with_the_jdk_fix(tmp_path):
    environment = java_practice(tmp_path, 21)
    attempt = started(environment, Language.JAVA)
    with pytest.raises(LanguageServerNotInstalledError) as refused:
        target(environment, attempt)
    assert str(refused.value).splitlines() == [
        "jdtls needs JDK 25 or 26, not 21.0.1",
        "fix: select a JDK 25 to 26 with JAVA_HOME, or install JDK 25: "
        "https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#jdk",
    ]


def test_a_server_that_runs_on_no_jdk_gets_no_java_home(practice):
    assert target(practice, started(practice, Language.PYTHON)).java_home is None


def test_a_project_attempt_is_rooted_in_its_folder(tmp_path):
    environment = project_environment(
        tmp_path, ScriptedProjectProcess(), language_servers=FakeLanguageServers(INSTALLED_SERVERS)
    )
    attempt = start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt
    found = target(environment, attempt)
    assert (found.server.name, found.root) == ("basedpyright", f"projects/{PROJECT_SLUG}")


def test_the_target_names_the_content_root_a_library_file_is_never_read_from(practice):
    assert (
        target(practice, started(practice, Language.PYTHON)).content_root == practice.content_root
    )


def test_the_target_names_the_directory_the_server_runs_in_and_the_servers_install(practice):
    found = target(practice, started(practice, Language.PYTHON))
    assert (found.directory, found.lsp_directory) == (
        practice.root / "python",
        practice.root / ".cs" / "lsp",
    )


def test_an_unknown_attempt_is_refused(practice):
    with pytest.raises(UnknownAttemptError):
        session_target(practice, ON, 41)


def test_an_attempt_that_ended_is_refused(practice):
    attempt = started(practice, Language.PYTHON)
    practice.progress.update_attempt(replace(attempt, status=AttemptStatus.PASSED))
    with pytest.raises(AttemptEndedError):
        target(practice, attempt)


def test_the_attempt_is_checked_before_the_preference(practice):
    with pytest.raises(UnknownAttemptError):
        session_target(practice, Preferences(), 41)


def test_the_preference_off_is_refused_with_the_way_to_turn_it_on(practice):
    attempt = started(practice, Language.PYTHON)
    with pytest.raises(UsageError, match="code intelligence is off: turn it on in Settings"):
        target(practice, attempt, Preferences())


def test_a_kotlin_attempt_gets_the_kotlin_lsp_rooted_in_the_jvm_project(practice):
    found = target(practice, started(practice, Language.KOTLIN))
    assert (found.server.name, found.root) == ("kotlin-lsp", "jvm")


def test_a_kotlin_session_imports_with_the_selected_jdk(practice):
    assert target(practice, started(practice, Language.KOTLIN)).java_home == JDK_HOME


def test_a_go_attempt_gets_gopls_rooted_in_the_go_project(practice):
    found = target(practice, started(practice, Language.GO))
    assert (found.server.name, found.root) == ("gopls", "go")


def test_a_rust_attempt_gets_rust_analyzer_rooted_in_the_rust_project(practice):
    found = target(practice, started(practice, Language.RUST))
    assert (found.server.name, found.root) == ("rust-analyzer", "rust")


def test_a_rust_session_reads_the_standard_library_from_links_of_its_root(practice):
    found = target(practice, started(practice, Language.RUST))
    assert found.standard_library_links == practice.root / ".cs/lsp/rust-library/rust"


def test_a_session_of_another_server_has_no_links_to_a_standard_library(practice):
    assert target(practice, started(practice, Language.GO)).standard_library_links is None


def test_a_rust_attempt_without_rust_analyzer_is_refused_with_the_rustup_fix(tmp_path):
    probes = {name: probe for name, probe in INSTALLED_SERVERS.items() if name != "rust-analyzer"}
    environment = make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=FakeLanguageServers(probes),
    )
    with pytest.raises(LanguageServerNotInstalledError) as refused:
        target(environment, started(environment, Language.RUST))
    assert str(refused.value).splitlines() == [
        "rust-analyzer is not installed",
        "fix: rustup component add rust-analyzer",
    ]


def test_a_go_attempt_whose_gopls_was_built_for_another_go_is_refused_with_the_fix(tmp_path):
    environment = make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=FakeLanguageServers(INSTALLED_SERVERS, go="1.26.1"),
    )
    with pytest.raises(LanguageServerNotInstalledError) as refused:
        target(environment, started(environment, Language.GO))
    assert str(refused.value).splitlines() == [
        "gopls 0.24.0 installed; cstudy needs 0.23.0",
        "fix: cstudy doctor --fix",
    ]


def test_a_kotlin_attempt_whose_license_is_not_accepted_is_refused_with_the_accept_command(
    tmp_path,
):
    environment = make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=FakeLanguageServers(INSTALLED_SERVERS, accepted=frozenset()),
    )
    with pytest.raises(LanguageServerNotInstalledError) as refused:
        target(environment, started(environment, Language.KOTLIN))
    assert str(refused.value).splitlines() == [
        "kotlin-lsp needs you to accept the JetBrains Free Plugin License Agreement 1.0",
        "fix: cstudy doctor --fix --accept-license kotlin-lsp",
    ]


def service_environment(tmp_path: Path, language: str = "typescript") -> Environment:
    root = make_content(tmp_path)
    write_problem(root, {**meta_document(), "languages": [language]})
    return make_environment(
        root, sandbox=FakeSandbox(), language_servers=FakeLanguageServers(INSTALLED_SERVERS)
    )


@pytest.fixture
def service_project(tmp_path) -> Environment:
    return service_environment(tmp_path)


def service_target(environment: Environment) -> SessionTarget:
    attempt = start_attempt(environment, StartRequest(SERVICE_SLUG)).attempt
    return target(environment, attempt)


def sidecar_of(found: SessionTarget) -> SidecarPlan:
    assert found.sidecar is not None
    return found.sidecar


def test_a_typescript_service_project_gets_its_server_in_a_sidecar_rooted_in_its_folder(
    service_project,
):
    """Sandboxed code writes that folder, so no server on this machine reads it."""
    found = service_target(service_project)

    assert (found.server.name, found.root, found.sidecar is not None) == (
        "typescript-language-server",
        f"projects/{SERVICE_SLUG}",
        True,
    )


def test_the_sidecars_typescript_runs_the_projects_own_compiler(service_project):
    found = service_target(service_project)
    options = found.server.initialization_options(str(found.workspace))

    assert options["tsserver"] == {"path": f"{found.directory}/node_modules/typescript/lib"}


def test_a_python_service_project_gets_basedpyright_in_a_sidecar(tmp_path):
    found = service_target(service_environment(tmp_path, "python"))

    assert (found.server.name, found.sidecar is not None) == ("basedpyright", True)


def test_a_practice_attempt_runs_its_server_on_this_machine(practice):
    assert target(practice, started(practice, Language.PYTHON)).sidecar is None


def test_the_sidecar_is_a_stack_of_its_own_owned_by_this_process(service_project):
    identity = sidecar_of(service_target(service_project)).identity

    assert (identity.kind, identity.slug, identity.owner_pid, identity.name[:12]) == (
        StackKind.LSP,
        SERVICE_SLUG,
        41,
        "cstudy-l-41-",
    )


def test_each_session_gets_a_sidecar_of_its_own(service_project):
    attempt = start_attempt(service_project, StartRequest(SERVICE_SLUG)).attempt

    first, second = (sidecar_of(target(service_project, attempt)) for _ in range(2))

    assert first.identity.name != second.identity.name


def test_the_sidecar_mounts_the_project_where_the_session_names_it(service_project):
    found = service_target(service_project)
    project = sidecar_of(found).project

    assert (project.path, project.source) == (
        str(found.directory),
        str(found.directory.resolve()),
    )


def test_the_sidecar_mounts_the_servers_of_the_workspace(service_project):
    found = service_target(service_project)

    assert sidecar_of(found).servers.path == str(found.lsp_directory)


def test_the_sidecar_writes_its_compose_file_among_the_runs(service_project):
    found = service_target(service_project)
    plan = sidecar_of(found)

    assert plan.run == str((found.workspace / ".cs" / "runs" / plan.identity.name).resolve())


def test_the_sidecar_runs_as_you(service_project):
    assert sidecar_of(service_target(service_project)).user == SandboxUser(501, 20)


def java_service_environment(tmp_path: Path, jdk: int = 25) -> Environment:
    root = make_content(tmp_path)
    write_problem(root, java_meta_document())
    return make_environment(
        root,
        sandbox=FakeSandbox(),
        language_servers=FakeLanguageServers(INSTALLED_SERVERS),
        jdk=jdk_of(jdk),
    )


def java_target(tmp_path: Path, jdk: int = 25) -> SessionTarget:
    return service_target(java_service_environment(tmp_path, jdk))


def test_a_java_service_project_gets_jdt_ls_in_a_sidecar_on_the_projects_image(tmp_path):
    found = java_target(tmp_path)

    assert (found.server.name, sidecar_of(found).image) == ("jdtls", GRADLE_IMAGE)


def test_the_java_sidecar_reads_the_projects_install_cache(tmp_path):
    found = java_target(tmp_path)
    toolchain = sidecar_of(found).toolchain
    workspace = workspace_digest(str(found.workspace.resolve()))

    assert toolchain is not None
    assert toolchain.cache_volume == f"cstudy-i-{SERVICE_SLUG}-{workspace}_cache"


def test_the_java_sidecar_keeps_its_data_in_its_own_runs_folder(tmp_path):
    plan = sidecar_of(java_target(tmp_path))

    assert plan.data_directory == f"{plan.run}/data"


def test_the_java_sidecar_needs_no_jdk_25_or_26_on_this_machine(tmp_path):
    """JDT LS runs on the image's JDK 25, whatever this machine selects."""
    found = java_target(tmp_path, 21)

    assert (found.server.jdks, found.java_home) == (None, None)


def test_a_service_projects_java_state_ignores_this_machines_jdk(tmp_path):
    environment = java_service_environment(tmp_path, 21)
    attempt = start_attempt(environment, StartRequest(SERVICE_SLUG)).attempt
    states = session_server_states(environment, attempt.id)

    java = next(state for state in states if state.language is Language.JAVA)
    assert java.status is ServerStatus.INSTALLED


def test_a_practice_java_attempt_still_needs_a_jdk_25_or_26(tmp_path):
    environment = java_service_environment(tmp_path, 21)
    states = session_server_states(environment, None)

    java = next(state for state in states if state.language is Language.JAVA)
    assert java.status is ServerStatus.NEEDS_JDK


def test_a_service_project_in_a_language_without_a_sidecar_server_has_none_yet(tmp_path):
    environment = service_environment(tmp_path, "kotlin")
    attempt = start_attempt(environment, StartRequest(SERVICE_SLUG)).attempt

    with pytest.raises(UsageError, match="no code intelligence for kotlin service projects yet"):
        target(environment, attempt)


@pytest.mark.parametrize(
    ("language", "reason"),
    [("kotlin", "its license"), ("rust", "no Rust service project")],
)
def test_the_refusal_says_why_from_the_route_table(tmp_path, language, reason):
    environment = service_environment(tmp_path, language)
    attempt = start_attempt(environment, StartRequest(SERVICE_SLUG)).attempt

    with pytest.raises(UsageError, match=reason):
        target(environment, attempt)


class WithoutPracticeProjects(FakeLanguageServers):
    """Every server is installed in `.cs/lsp/`, and the workspace's `typescript/` has no
    `node_modules`, as for a learner who works on service projects only."""

    def probe(self, server: LanguageServer) -> ServerProbe:
        requirement = server.requirement
        return FileMissing(requirement.path) if requirement else super().probe(server)


def without_practice_projects(tmp_path: Path, language: str = "typescript") -> Environment:
    root = make_content(tmp_path)
    write_problem(root, {**meta_document(), "languages": [language]})
    servers = WithoutPracticeProjects(INSTALLED_SERVERS)
    return make_environment(root, sandbox=FakeSandbox(), language_servers=servers)


def typescript_state(environment: Environment, attempt_id: int | None) -> LanguageServerState:
    states = session_server_states(environment, attempt_id)
    return next(state for state in states if state.language is Language.TYPESCRIPT)


def test_a_service_projects_typescript_needs_no_practice_project_of_the_workspace(tmp_path):
    environment = without_practice_projects(tmp_path)
    attempt = start_attempt(environment, StartRequest(SERVICE_SLUG)).attempt

    assert typescript_state(environment, attempt.id).status is ServerStatus.INSTALLED


def test_without_an_attempt_typescript_still_needs_the_workspaces_practice_project(tmp_path):
    environment = without_practice_projects(tmp_path)

    assert typescript_state(environment, None).status is ServerStatus.NOT_INSTALLED


def test_a_practice_attempts_typescript_needs_the_workspaces_practice_project(practice, tmp_path):
    environment = replace(practice, language_servers=WithoutPracticeProjects(INSTALLED_SERVERS))
    attempt = started(environment, Language.TYPESCRIPT)

    assert typescript_state(environment, attempt.id).status is ServerStatus.NOT_INSTALLED


def test_an_unknown_attempt_gets_the_workspaces_states(tmp_path):
    environment = without_practice_projects(tmp_path)

    assert typescript_state(environment, 99).status is ServerStatus.NOT_INSTALLED


def test_an_items_attempt_gets_the_workspaces_states(practice):
    attempt = start_item_attempt(practice, ItemStartRequest("url-shortener")).attempt

    assert len(session_server_states(practice, attempt.id)) == len(Language)


def test_a_service_project_session_needs_no_practice_project_either(tmp_path):
    environment = without_practice_projects(tmp_path)
    attempt = start_attempt(environment, StartRequest(SERVICE_SLUG)).attempt

    assert target(environment, attempt).server.name == "typescript-language-server"


def test_an_item_has_no_code(practice):
    attempt = start_item_attempt(practice, ItemStartRequest("url-shortener")).attempt
    with pytest.raises(UsageError, match="url-shortener has no code"):
        target(practice, attempt)


def test_a_server_that_is_not_installed_is_refused_with_the_fix(tmp_path):
    environment = make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=STUBS),
    )
    attempt = started(environment, Language.PYTHON)
    with pytest.raises(LanguageServerNotInstalledError) as refused:
        target(environment, attempt)
    assert str(refused.value) == "basedpyright is not installed\nfix: cstudy doctor --fix"


def test_a_server_of_another_version_is_refused_naming_both(tmp_path):
    probes = {**INSTALLED_SERVERS, "basedpyright": VersionPrinted("basedpyright 1.39.0\n")}
    environment = make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=FakeLanguageServers(probes),
    )
    attempt = started(environment, Language.PYTHON)
    with pytest.raises(LanguageServerNotInstalledError) as refused:
        target(environment, attempt)
    assert str(refused.value).splitlines()[0] == (
        "basedpyright 1.39.0 installed; cstudy needs 1.40.2"
    )


def test_a_version_command_that_fails_is_refused_in_its_own_words(tmp_path):
    probes = {**INSTALLED_SERVERS, "basedpyright": VersionFailed("Error: no module")}
    environment = make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=FakeLanguageServers(probes),
    )
    attempt = started(environment, Language.PYTHON)
    with pytest.raises(LanguageServerNotInstalledError, match="Error: no module"):
        target(environment, attempt)


def test_only_the_attempts_server_is_probed(practice):
    attempt = started(practice, Language.PYTHON)
    target(practice, attempt)
    assert practice.language_servers.probed == ["basedpyright"]  # type: ignore[attr-defined]


def test_the_places_no_server_or_library_file_may_show_are_the_references_cases_runs_and_content(
    practice,
):
    found = target(practice, started(practice, Language.PYTHON))
    workspace = found.workspace
    assert found.hidden == (
        workspace / ".cs" / "build",
        workspace / ".cs" / "cases",
        workspace / ".cs" / "runs",
        found.content_root,
    )
