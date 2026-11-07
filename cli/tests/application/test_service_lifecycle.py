"""A service project's lifecycle through a fake engine: start, install rules, and `cstudy test` on
two clocks."""

import json
from dataclasses import replace

import pytest

from coding_study.application.project_workspace import seed_project
from coding_study.application.service_lifecycle import (
    ServiceTestRequest,
    finish_service_start,
    install_dependencies,
    needs_install,
    preview_service_start,
    run_service_tests,
    service_needs_of,
)
from coding_study.application.service_stacks import (
    dev_stack_plan,
    graded_stack_plan,
)
from coding_study.application.service_stacks import (
    test_stack_plan as stack_plan_for_test,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import (
    PYTHON_IMAGE,
    CommandOutcome,
    SandboxInventory,
    StackContainer,
    StackKind,
    StackStartError,
    StartupBudget,
    StartupFailure,
    workspace_digest,
)
from tests.fakes import make_environment
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    CONFIG,
    FOLDER,
    IMAGE,
    INSTALL,
    LOCK,
    SLUG,
    make_content,
    meta_document,
    write_mock,
    write_problem,
)


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox()


@pytest.fixture
def environment(tmp_path, engine):
    root = make_content(tmp_path)
    write_problem(root)
    return make_environment(root, sandbox=engine)


def started(environment) -> None:
    start_attempt(environment, StartRequest(SLUG))


def problem_of(environment):
    return environment.problems.load(SLUG)


def notes() -> list[str]:
    return []


def test_a_new_attempt_copies_the_starter(environment):
    started(environment)

    assert environment.workspace.exists(f"{FOLDER}/src/server.ts")
    assert environment.workspace.exists(f"{FOLDER}/.env")


def test_a_new_attempt_writes_no_level_tests(environment):
    started(environment)

    assert not environment.workspace.exists(f"{FOLDER}/tests")


def test_a_new_attempt_links_no_toolchain(environment):
    started(environment)

    assert not (environment.root / FOLDER / ".venv").is_symlink()


def test_a_new_attempt_asks_the_engine_nothing(environment, engine):
    started(environment)

    assert engine.calls == []


def test_a_resumed_attempt_keeps_the_folder(environment):
    started(environment)
    (environment.root / FOLDER / "src" / "server.ts").write_text("// mine\n")

    again = start_attempt(environment, StartRequest(SLUG))

    assert again.resumed
    assert (environment.root / FOLDER / "src" / "server.ts").read_text() == "// mine\n"


def test_a_link_left_in_the_folder_is_never_written_through(environment, tmp_path):
    started(environment)
    outside = tmp_path / "outside.txt"
    target = environment.root / FOLDER / "README.md"
    target.unlink()
    target.symlink_to(outside)

    with pytest.raises(SandboxError, match=r"README\.md"):
        seed_project(environment.workspace, problem_of(environment))

    assert not outside.exists()


def test_preview_starts_a_stopped_engine(environment, engine):
    engine.engine = EngineState(EngineStatus.STOPPED)

    preview_service_start(environment, problem_of(environment), notes().append)

    assert engine.called("start_engine")


def test_preview_refuses_before_anything_is_written_without_docker(environment, engine):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    with pytest.raises(SandboxError, match=r"docs\.docker\.com"):
        preview_service_start(environment, problem_of(environment), notes().append)

    assert not environment.workspace.exists(FOLDER)


def test_preview_sweeps_this_workspaces_leftovers(environment, engine):
    digest = workspace_digest(str(environment.root.resolve()))
    engine.inventory_found = SandboxInventory(
        containers=(
            StackContainer("cstudy-t-1-a", "test", digest, 1),
            StackContainer("cstudy-t-2-a", "test", "other-workspace", 2),
        )
    )

    preview_service_start(environment, problem_of(environment), notes().append)

    assert [stack.name for stack in engine.called("remove_stack")] == ["cstudy-t-1-a"]


def test_preview_names_what_would_download(environment, engine):
    engine.every_image_present = False
    engine.present = {PYTHON_IMAGE}

    preview = preview_service_start(environment, problem_of(environment), notes().append)

    assert preview.missing_images == (IMAGE,)
    assert preview.downloads


def test_preview_with_everything_here_downloads_nothing(environment, engine):
    started(environment)
    installed(environment)

    preview = preview_service_start(environment, problem_of(environment), notes().append)

    assert not preview.downloads


def test_preview_counts_the_install_as_a_download(environment):
    started(environment)

    assert preview_service_start(environment, problem_of(environment), notes().append).downloads


def test_preview_downloads_nothing_is_written(environment, engine):
    preview_service_start(environment, problem_of(environment), notes().append)

    assert not engine.called("pull")
    assert not engine.called("install")


def test_finish_pulls_then_installs(environment, engine):
    started(environment)
    engine.every_image_present = False

    finish_service_start(environment, problem_of(environment), notes().append)

    names = [name for name, _ in engine.calls if name in ("pull", "install")]
    assert names == ["pull", "pull", "install"]
    assert set(engine.called("pull")) == {IMAGE, PYTHON_IMAGE}


def test_install_says_what_it_can_reach(environment):
    started(environment)
    lines: list[str] = []

    install_dependencies(environment, problem_of(environment), lines.append)

    assert any("your LAN" in line and "loopback" in line for line in lines)


def test_install_runs_with_its_limit_and_its_own_project(environment, engine):
    started(environment)

    install_dependencies(environment, problem_of(environment), notes().append)

    plan = engine.called("install")[0]
    assert plan.identity.kind is StackKind.INSTALL
    assert plan.identity.name.startswith(f"cstudy-i-{SLUG}-")
    assert plan.command == tuple(INSTALL)
    assert plan.environment == {"COREPACK_HOME": "/cache/corepack"}
    assert engine.install_timeouts == [600]


def test_install_is_guarded_and_always_stopped(environment, engine):
    started(environment)
    engine.install_outcome = CommandOutcome(1, "failed\n")

    with pytest.raises(SandboxError):
        install_dependencies(environment, problem_of(environment), notes().append)

    names = [name for name, _ in engine.calls]
    assert names == ["guard", "install", "stop_install", "guard_released"]


def test_a_failed_install_names_the_command_its_output_and_the_retry(environment, engine):
    started(environment)
    engine.install_outcome = CommandOutcome(1, "ERR_PNPM_FETCH_404\n")

    with pytest.raises(SandboxError) as caught:
        install_dependencies(environment, problem_of(environment), notes().append)

    text = str(caught.value)
    assert "corepack pnpm install" in text
    assert "ERR_PNPM_FETCH_404" in text
    assert f"cstudy start {SLUG}" in text


def test_a_failed_install_keeps_the_attempt(environment, engine):
    started(environment)
    engine.install_outcome = CommandOutcome(1, "failed\n")

    with pytest.raises(SandboxError):
        install_dependencies(environment, problem_of(environment), notes().append)

    assert environment.progress.active_attempt(SLUG) is not None


def test_a_failed_install_records_nothing(environment, engine):
    started(environment)
    engine.install_outcome = CommandOutcome(1, "failed\n")

    with pytest.raises(SandboxError):
        install_dependencies(environment, problem_of(environment), notes().append)

    assert needs_install(environment, problem_of(environment))


def test_an_install_past_its_limit_says_so(environment, engine):
    started(environment)
    engine.install_outcome = CommandOutcome(124, "", timed_out=True)

    with pytest.raises(SandboxError, match="600 s"):
        install_dependencies(environment, problem_of(environment), notes().append)


def installed(environment) -> None:
    (environment.root / FOLDER / "node_modules").mkdir(parents=True, exist_ok=True)
    install_dependencies(environment, problem_of(environment), notes().append)


def test_no_install_is_needed_once_the_record_holds_the_locks_digest(environment):
    started(environment)
    installed(environment)

    assert not needs_install(environment, problem_of(environment))


def test_the_record_is_written_under_the_project_files(environment):
    started(environment)
    installed(environment)

    assert environment.workspace.exists(f".cs/projects/{SLUG}.install.json")


def test_a_changed_lock_needs_an_install(environment):
    started(environment)
    installed(environment)

    (environment.root / FOLDER / LOCK).write_text("lockfileVersion: '9.1'\n")

    assert needs_install(environment, problem_of(environment))


def test_a_removed_node_modules_needs_an_install(environment):
    started(environment)
    installed(environment)
    (environment.root / FOLDER / "node_modules").rmdir()

    assert needs_install(environment, problem_of(environment))


def test_an_install_that_changes_the_lock_fails(environment, engine):
    """The lock is the contract: an install must use it exactly."""
    started(environment)

    def rewrite() -> None:
        (environment.root / FOLDER / LOCK).write_text("rewritten\n")

    engine.after_install = rewrite

    with pytest.raises(SandboxError, match="changed its lock file"):
        install_dependencies(environment, problem_of(environment), notes().append)


def test_a_missing_lock_says_how_to_get_it_back(environment):
    started(environment)
    (environment.root / FOLDER / LOCK).unlink()

    with pytest.raises(SandboxError, match=f"cstudy start --restore {LOCK}"):
        install_dependencies(environment, problem_of(environment), notes().append)


def test_a_problem_with_no_install_needs_none(tmp_path, engine):
    root = make_content(tmp_path)
    document = meta_document()
    project = document["project"]
    project["commands"].pop("install")  # type: ignore[index, union-attr]
    project["requires"].pop("lock")  # type: ignore[index, union-attr]
    write_problem(root, document)
    environment = make_environment(root, sandbox=engine)
    started(environment)

    assert not needs_install(environment, problem_of(environment))


def test_the_test_stack_is_a_test_stack_of_this_owner(environment, engine):
    started(environment)

    plan = stack_plan_for_test(environment, problem_of(environment))

    assert plan.identity.kind is StackKind.TEST
    assert plan.identity.slug == SLUG
    assert plan.identity.owner_pid == engine.owner_pid()
    assert plan.identity.name.startswith(f"cstudy-t-{engine.owner_pid()}-")


def test_two_test_stacks_have_different_names(environment):
    started(environment)
    problem = problem_of(environment)

    assert (
        stack_plan_for_test(environment, problem).identity.name
        != stack_plan_for_test(environment, problem).identity.name
    )


def test_the_test_stack_mounts_the_resolved_project_folder(environment):
    started(environment)

    plan = stack_plan_for_test(environment, problem_of(environment))

    assert plan.paths.project == str((environment.root / FOLDER).resolve())
    assert plan.paths.run.endswith(f".cs/runs/{plan.identity.name}")


def test_the_test_stack_runs_the_manifests_commands(environment):
    started(environment)

    plan = stack_plan_for_test(environment, problem_of(environment))

    assert plan.app.command == ("node", "src/server.ts")
    assert plan.app.image == IMAGE
    assert plan.app.environment == {"PORT": "8000"}
    assert plan.app.health == "/health"
    assert plan.bootstrap is not None
    assert plan.bootstrap.command == ("node", "scripts/migrate.ts")


def test_the_budget_comes_from_the_manifest(environment):
    assert problem_of(environment).meta.project.service.startup_budget == StartupBudget(300, 45)  # type: ignore[union-attr]


def run_tests(environment, **changes) -> object:
    request = replace(ServiceTestRequest(SLUG), **changes)
    return run_service_tests(environment, request, notes().append)


def test_cstudy_test_starts_a_stack_runs_the_command_and_stops(environment, engine):
    started(environment)

    result = run_tests(environment)

    names = [name for name, _ in engine.calls]
    assert names[names.index("guard", names.index("stop_install")) :] == [
        "guard",
        "start",
        "exec_app",
        "stop",
        "guard_released",
    ]
    assert result.passed


def test_the_test_command_runs_with_its_own_limit(environment, engine):
    started(environment)

    run_tests(environment)

    command = engine.called("exec_app")[0]
    assert command.command == ("node", "--test")
    assert command.timeout_s == 120


def test_a_timeouts_entry_overrides_the_test_limit(tmp_path, engine):
    root = make_content(tmp_path)
    write_problem(root, meta_document(timeouts_s={"test": 7, "startup": 900}))
    environment = make_environment(root, sandbox=engine)
    started(environment)

    run_tests(environment)

    assert engine.called("exec_app")[0].timeout_s == 7
    assert engine.called("start")[0] == StartupBudget(900, 45)


def test_a_failing_test_command_is_a_failed_result_not_an_error(environment, engine):
    started(environment)
    engine.exec_outcome = CommandOutcome(1, "1 failing\n")

    result = run_tests(environment)

    assert not result.passed
    assert result.outcome.exit_code == 1


def test_run_time_excludes_startup(environment, engine):
    """The owner's rule: limits and reported run times start once everything is running."""
    started(environment)
    engine.started_at, engine.ready_at = 10.0, 73.0

    result = run_tests(environment)

    assert result.startup_seconds == 63.0
    assert result.test_seconds == pytest.approx(0.25)
    assert result.total_seconds == pytest.approx(
        result.startup_seconds + result.test_seconds + result.cases_seconds
    )


@pytest.mark.parametrize(
    "failure",
    [StartupFailure.BOOTSTRAP, StartupFailure.APP_EXITED, StartupFailure.HEALTH_TIMEOUT],
)
def test_a_start_your_code_failed_is_reported_without_raising(environment, engine, failure):
    started(environment)
    engine.start_error = StackStartError(failure, "your code", "the output\n")

    result = run_tests(environment)

    assert result.failure is not None
    assert result.failure.failure is failure
    assert result.outcome is None
    assert not result.passed


@pytest.mark.parametrize("failure", [StartupFailure.SERVICE, StartupFailure.GRADE_SETUP])
def test_a_start_that_is_not_your_code_raises(environment, engine, failure):
    started(environment)
    engine.start_error = StackStartError(failure, "not your code")

    with pytest.raises(StackStartError):
        run_tests(environment)


def test_a_startup_failure_runs_no_test_and_still_stops_the_stack(environment, engine):
    started(environment)
    engine.start_error = StackStartError(StartupFailure.APP_EXITED, "no")

    run_tests(environment)

    assert not engine.called("exec_app")
    assert engine.called("stop")


def test_cstudy_test_stores_nothing(environment):
    started(environment)
    attempt = environment.progress.active_attempt(SLUG)

    run_tests(environment)

    assert environment.progress.test_runs(attempt.id) == ()


def test_cstudy_test_installs_when_the_lock_changed(environment, engine):
    started(environment)
    installed(environment)
    (environment.root / FOLDER / LOCK).write_text("changed\n")
    before = len(engine.called("install"))

    run_tests(environment)

    assert len(engine.called("install")) == before + 1


def test_cstudy_test_sweeps_first(environment, engine):
    started(environment)

    run_tests(environment)

    names = [name for name, _ in engine.calls]
    assert names.index("inventory") < names.index("start")


def with_vendor(tmp_path, engine):
    root = make_content(tmp_path)
    write_problem(root, meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}]))
    write_mock(root)
    environment = make_environment(root, sandbox=engine)
    started(environment)
    return environment


def test_a_test_stack_renders_visible_scenarios_only(tmp_path, engine):
    environment = with_vendor(tmp_path, engine)

    plan = stack_plan_for_test(environment, problem_of(environment))

    assert plan.mocks is not None
    scenarios = json.loads(plan.mocks.rendered_config)["mocks"]["room-vendor"]["scenarios"]
    assert sorted(scenarios) == ["outage"]


def test_a_graded_stack_renders_every_scenario(tmp_path, engine):
    environment = with_vendor(tmp_path, engine)

    plan = graded_stack_plan(environment, problem_of(environment), 1)

    assert plan.mocks is not None
    scenarios = json.loads(plan.mocks.rendered_config)["mocks"]["room-vendor"]["scenarios"]
    assert sorted(scenarios) == ["outage", "rate_limited"]


def test_each_stack_has_a_control_token_of_its_own(tmp_path, engine):
    environment = with_vendor(tmp_path, engine)
    problem = problem_of(environment)

    first, second = (stack_plan_for_test(environment, problem) for _ in range(2))

    assert first.mocks is not None and second.mocks is not None
    assert first.mocks.control_token != second.mocks.control_token


def test_each_mock_server_is_an_alias_of_the_container(tmp_path, engine):
    environment = with_vendor(tmp_path, engine)

    plan = stack_plan_for_test(environment, problem_of(environment))

    assert plan.mocks is not None
    assert plan.mocks.aliases == ("room-vendor",)


def test_a_test_stack_gives_commands_test_its_control_interface(tmp_path, engine):
    environment = with_vendor(tmp_path, engine)

    run_tests(environment)

    command = engine.called("exec_app")[0]
    assert set(command.environment) == {"CSTUDY_MOCK_CONTROL_URL", "CSTUDY_MOCK_CONTROL_TOKEN"}


def test_a_graded_stack_prepares_its_reset_after_bootstrap(environment):
    started(environment)

    plan = graded_stack_plan(environment, problem_of(environment), 1)

    assert plan.reset_prepare is not None
    assert plan.reset_prepare.command == ("node", "scripts/reset.ts")


def test_a_dev_stack_has_no_reset_to_prepare(environment):
    started(environment)

    assert dev_stack_plan(environment, problem_of(environment)).reset_prepare is None


def test_a_dev_stack_has_a_stable_name_and_keeps_its_data(environment):
    started(environment)
    problem = problem_of(environment)

    plan = dev_stack_plan(environment, problem)

    assert plan.identity.name == dev_stack_plan(environment, problem).identity.name
    assert not plan.identity.kind.removes_volumes


def test_grade_setup_expands_the_problems_folder(tmp_path, engine):
    root = make_content(tmp_path)
    document = meta_document()
    commands = document["project"]["commands"]  # type: ignore[index]
    commands["grade_setup"] = ["node", "{problem}/grading/setup.ts"]  # type: ignore[index]
    write_problem(root, document)
    environment = make_environment(root, sandbox=engine)
    started(environment)

    plan = graded_stack_plan(environment, problem_of(environment), 2)

    assert plan.grade_setup is not None
    assert plan.grade_setup.command == ("node", "/cstudy/problem/grading/setup.ts")
    assert plan.grade_setup.graded_level == 2
    assert plan.grade_setup.grading_directory.endswith("/grading")


def test_backing_services_wait_for_their_phase(tmp_path, engine):
    root = make_content(tmp_path)
    write_problem(root, meta_document(services="services/compose.yaml"))
    compose = root / "problems" / f"0901-{SLUG}" / "services" / "compose.yaml"
    compose.parent.mkdir()
    compose.write_text("services: {}\n")
    environment = make_environment(root, sandbox=engine)
    started(environment)

    with pytest.raises(SandboxError, match="backing services"):
        run_tests(environment)


def test_the_needs_of_a_service_project_list_what_it_depends_on(environment):
    rows = {row.label: row for row in service_needs_of(environment, SLUG) or ()}

    assert set(rows) == {"docker", "language", "packages", "total"}
    assert "typescript" in rows["language"].text
    assert "node:24-slim" in rows["language"].text
    assert "77 MB" in rows["language"].text
    assert "pnpm" in rows["packages"].text
    assert "40 MB" in rows["packages"].text
    assert "300 MB memory" in rows["total"].text


def test_a_running_engine_meets_the_docker_need(environment):
    rows = {row.label: row for row in service_needs_of(environment, SLUG) or ()}

    assert rows["docker"].problem is None


def test_a_missing_engine_is_named_with_the_install_message(environment, engine):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    rows = {row.label: row for row in service_needs_of(environment, SLUG) or ()}

    assert "docs.docker.com" in (rows["docker"].problem or "")


def test_a_stopped_engine_is_no_problem_since_start_starts_it(environment, engine):
    engine.engine = EngineState(EngineStatus.STOPPED)

    rows = {row.label: row for row in service_needs_of(environment, SLUG) or ()}

    assert rows["docker"].problem is None
    assert "not running" in rows["docker"].text
    assert not engine.called("start_engine")


def test_a_bank_problem_has_no_needs_and_asks_the_engine_nothing(tmp_path, engine):
    root = make_content(tmp_path)
    environment = make_environment(root, sandbox=engine)
    slug = environment.problems.list_summaries()[0].meta.slug

    assert service_needs_of(environment, slug) is None
    assert engine.calls == []
