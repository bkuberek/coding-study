"""A Go service project's install builds gopls into the project's install cache while code
intelligence is on, where its sidecar runs it (docs/specs/service-projects.md#language-servers):
the gopls of `.cs/lsp/` is built for this machine, and the sidecar runs Linux."""

import json
from pathlib import Path

import pytest

from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.application.code_intelligence import (
    ServerStatus,
    session_server_states,
    session_target,
)
from coding_study.application.environment import Environment
from coding_study.application.service_lifecycle import (
    install_dependencies,
    needs_install,
    server_in_install_cache,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.code_intelligence import GOPLS, CacheInstall, Launch, cache_install
from coding_study.domain.errors import LanguageServerNotInstalledError
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from coding_study.domain.sandbox import CommandOutcome, InstallPlan
from tests.fakes import INSTALLED_SERVERS, FakeLanguageServers, make_environment
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import GO_IMAGE, SLUG, make_content, write_go_problem

ON = Preferences(code_intelligence=True)


def gopls_in_cache() -> CacheInstall:
    install = cache_install(GOPLS)
    assert install is not None
    return install


GOPLS_IN_CACHE = gopls_in_cache()


def go_environment(tmp_path: Path, engine: FakeSandbox, preferences: Preferences) -> Environment:
    root = make_content(tmp_path)
    write_go_problem(root)
    FsPreferencesStore(root).write(preferences_document(preferences))
    environment = make_environment(
        root, sandbox=engine, language_servers=FakeLanguageServers(INSTALLED_SERVERS)
    )
    start_attempt(environment, StartRequest(SLUG))
    return environment


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox()


@pytest.fixture
def on(tmp_path, engine) -> Environment:
    return go_environment(tmp_path, engine, ON)


@pytest.fixture
def off(tmp_path, engine) -> Environment:
    return go_environment(tmp_path, engine, Preferences())


def install(environment: Environment, lines: list[str] | None = None) -> None:
    problem = environment.problems.load(SLUG)
    install_dependencies(environment, problem, (lines if lines is not None else []).append)


def installs(engine: FakeSandbox) -> list[InstallPlan]:
    return [plan for plan in engine.called("install") if isinstance(plan, InstallPlan)]


def test_the_install_builds_gopls_into_the_install_cache_after_the_projects_own(on, engine):
    install(on)

    assert [plan.command for plan in installs(engine)] == [
        ("go", "mod", "download"),
        GOPLS_IN_CACHE.command,
    ]


def test_gopls_builds_with_the_installs_network_and_its_variables(on, engine):
    install(on)

    plan = installs(engine)[1]
    assert (plan.image, plan.environment["GOWORK"], plan.environment["GOBIN"]) == (
        GO_IMAGE,
        "off",
        "/cache/gopls/0.24.0",
    )


def test_its_modules_and_build_go_to_a_scratch_folder_that_go_clean_empties():
    assert (GOPLS_IN_CACHE.environment["GOMODCACHE"], GOPLS_IN_CACHE.command[2]) == (
        "/cache/gopls/scratch/mod",
        'mkdir -p "$GOTMPDIR" && go install "$1" && go clean -cache -modcache',
    )


def test_the_record_names_the_gopls_the_install_built(on):
    install(on)

    assert server_in_install_cache(on, SLUG, "gopls") == "0.24.0"


def test_with_code_intelligence_off_the_install_builds_no_server(off, engine):
    install(off)

    assert len(installs(engine)) == 1


def test_a_gopls_that_does_not_build_is_said_and_the_project_stays_installed(on, engine):
    def gopls_fails() -> None:
        """The project's install passes, gopls's, the second, fails."""
        if len(installs(engine)) == 2:
            engine.install_outcome = CommandOutcome(1, "no network\n")

    engine.after_install = gopls_fails
    lines: list[str] = []

    install(on, lines)

    assert server_in_install_cache(on, SLUG, "gopls") is None
    assert any("gopls 0.24.0 was not installed" in line for line in lines)


def test_an_install_without_gopls_is_due_once_code_intelligence_is_on(off, engine):
    install(off)
    FsPreferencesStore(off.root).write(preferences_document(ON))

    assert needs_install(off, off.problems.load(SLUG))


def test_an_install_that_built_gopls_is_not_due_again(on):
    install(on)

    assert not needs_install(on, on.problems.load(SLUG))


def test_with_code_intelligence_off_a_missing_gopls_is_no_reason_to_install(off):
    install(off)

    assert not needs_install(off, off.problems.load(SLUG))


def go_state(environment: Environment):
    attempt = environment.progress.active_attempt(SLUG)
    assert attempt is not None
    states = session_server_states(environment, attempt.id)
    return next(state for state in states if state.language is Language.GO)


def test_before_the_install_built_it_gopls_is_not_installed_with_the_fix(on):
    state = go_state(on)

    assert (state.status, state.detail) == (
        ServerStatus.NOT_INSTALLED,
        "not in the project's install cache: run cstudy test",
    )


def test_once_built_gopls_is_installed_whatever_this_machine_holds(on):
    install(on)

    assert go_state(on).detail == "gopls 0.24.0"


def test_a_session_before_the_install_built_gopls_is_refused_naming_the_fix(on):
    attempt = on.progress.active_attempt(SLUG)
    assert attempt is not None

    with pytest.raises(LanguageServerNotInstalledError, match="not in the project's install"):
        session_target(on, ON, attempt.id)


def test_a_session_runs_the_gopls_of_the_install_cache_in_a_sidecar(on):
    install(on)
    attempt = on.progress.active_attempt(SLUG)
    assert attempt is not None

    found = session_target(on, ON, attempt.id)

    assert found.sidecar is not None
    launch = Launch(str(found.lsp_directory), platform="linux")
    assert found.server.command(launch) == ("/cache/gopls/0.24.0/gopls",)


def test_the_record_stays_json_with_the_lock(on):
    install(on)

    record = json.loads((on.root / ".cs" / "projects" / f"{SLUG}.install.json").read_text())
    assert set(record) == {"lock_sha256", "servers"}
