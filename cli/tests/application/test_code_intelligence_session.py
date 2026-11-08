"""Which server and root a code-intelligence session gets from an attempt
(docs/specs/web-ui.md#sessions, docs/specs/web-ui.md#language-servers)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.code_intelligence import session_target
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator, VersionFailed, VersionPrinted
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.errors import (
    AttemptEndedError,
    LanguageServerNotInstalledError,
    UnknownAttemptError,
    UsageError,
)
from coding_study.domain.preferences import Preferences
from coding_study.domain.problem import Language
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
from tests.service_problems import SLUG as SERVICE_SLUG
from tests.service_problems import make_content, write_problem

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


@pytest.mark.parametrize("language", [Language.GO, Language.RUST, Language.KOTLIN])
def test_a_language_without_a_server_in_this_phase_is_refused(practice, language):
    attempt = started(practice, language)
    with pytest.raises(UsageError, match=f"no code intelligence for {language.value} yet"):
        target(practice, attempt)


def test_the_language_is_checked_before_the_server_is_looked_for(tmp_path):
    environment = make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        toolchains=FakeToolchains(stub_generators=STUBS),
    )
    attempt = started(environment, Language.GO)
    with pytest.raises(UsageError, match="no code intelligence for go yet"):
        target(environment, attempt)


@pytest.fixture
def service_project(tmp_path) -> Environment:
    root = make_content(tmp_path)
    write_problem(root)
    return make_environment(
        root, sandbox=FakeSandbox(), language_servers=FakeLanguageServers(INSTALLED_SERVERS)
    )


def test_a_service_project_gets_no_server_on_this_machine(service_project):
    """Sandboxed code writes that folder, and a server here would read it: P9 brings a sidecar."""
    attempt = start_attempt(service_project, StartRequest(SERVICE_SLUG)).attempt

    with pytest.raises(UsageError, match="no code intelligence for typescript yet"):
        target(service_project, attempt)


def test_a_service_project_probes_no_server(service_project):
    attempt = start_attempt(service_project, StartRequest(SERVICE_SLUG)).attempt

    with pytest.raises(UsageError):
        target(service_project, attempt)

    assert service_project.language_servers.probed == []  # type: ignore[attr-defined]


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
