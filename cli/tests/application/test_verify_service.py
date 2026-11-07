"""D1, D3, D9 and D11 of `cstudy verify` on a service project, through a fake engine and fake HTTP
clients."""

from pathlib import Path
from typing import Any

import pytest

from coding_study.application.http_grading_ports import StackClients, StackEndpoints
from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.application.verify_projects import PROJECT_BUILDS, STARTER_BUILDS
from coding_study.application.verify_service import ServiceVerification, verify_service_project
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.http_grading import ExchangeFailed, ExchangeFailure, HttpResponse
from coding_study.domain.problem import Language
from coding_study.domain.sandbox import CommandOutcome, StackKind, StackStartError, StartupFailure
from tests.application.http_grading_fakes import FakeApp, FakeMockControl
from tests.fakes import make_environment
from tests.real_service_projects import PYTHON, TYPESCRIPT, copy_fixture
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    CONFIG,
    SLUG,
    make_content,
    meta_document,
    write_cases,
    write_mock,
    write_problem,
)

RIGHT = HttpResponse(200, {}, b'{"ok": true}', 5_000_000)
WRONG = HttpResponse(500, {}, b"{}", 5_000_000)
INSTALLED_BYTES = 40_000_000
CASES = [
    {
        "id": "v1",
        "level": 1,
        "visible": True,
        "request": {"method": "GET", "path": "/a"},
        "expected": {"status": 200, "body": {"ok": True}},
    },
    {
        "id": "h1",
        "level": 1,
        "request": {"method": "GET", "path": "/a"},
        "expected": {"status": 200, "body": {"ok": True}},
    },
]


@pytest.fixture
def engine() -> FakeSandbox:
    found = FakeSandbox(control_port=5001)

    def installed() -> None:
        plan = found.called("install")[-1]
        folder = Path(plan.paths.project) / "node_modules"  # type: ignore[attr-defined]
        folder.mkdir(exist_ok=True)
        with (folder / "package").open("wb") as file:
            file.truncate(INSTALLED_BYTES)

    found.after_install = installed
    return found


@pytest.fixture
def app() -> FakeApp:
    return FakeApp([], answers={"/a": RIGHT})


@pytest.fixture
def environment(tmp_path, engine, app):
    root = make_content(tmp_path)
    write_problem(root, meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}]))
    write_mock(root)
    write_cases(root, CASES)

    def clients(_endpoints: StackEndpoints) -> StackClients:
        return StackClients(app, FakeMockControl([]))

    return make_environment(root, sandbox=engine, stack_clients=clients)


def verified(environment) -> ServiceVerification:
    problem = environment.problems.load(SLUG)
    return verify_service_project(environment, problem, Language.TYPESCRIPT, lambda _line: None)


def test_a_good_problem_passes(environment):
    result = verified(environment)

    assert result.language.passed
    assert result.suite.passed
    assert result.d11_problems == ()


def test_the_reference_runs_in_its_own_build_folder(environment, engine):
    verified(environment)

    assert all(".cs/" in plan.paths.project for plan in engine.plans)


def test_it_writes_the_starter_and_the_reference_without_generated_tests(environment):
    verified(environment)

    assert environment.workspace.exists(f".cs/build/projects/{SLUG}/reference/src/server.ts")


def test_the_starters_and_the_references_builds_hold_the_env_file(environment):
    verified(environment)

    workspace = environment.workspace
    assert workspace.read_text(f"{PROJECT_BUILDS}/{SLUG}/reference/.env") == "PORT=8000\n"
    assert workspace.read_text(f"{STARTER_BUILDS}/{SLUG}/.env") == "PORT=8000\n"


def test_it_installs_for_the_starter_and_for_the_reference(environment, engine):
    verified(environment)

    assert len(engine.called("install")) == 2


def test_it_pulls_what_is_missing_before_any_stack(environment, engine):
    engine.every_image_present = False

    verified(environment)

    names = [name for name, _ in engine.calls]
    assert names.index("pull") < names.index("install") < names.index("start")


def test_every_stack_comes_down(environment, engine):
    verified(environment)

    assert len(engine.called("stop")) == len(engine.called("start"))


def test_grading_uses_graded_stacks_and_the_suite_a_test_stack(environment, engine):
    verified(environment)

    kinds = [plan.identity.kind for plan in engine.plans]
    assert kinds.count(StackKind.TEST) == 2
    assert kinds.count(StackKind.GRADED) == 4


def test_a_failing_reference_fails_d3(environment, app):
    app.answers["/a"] = WRONG

    result = verified(environment)

    assert not result.language.passed


def test_a_starter_whose_cases_fail_still_passes_d1(environment, app):
    app.answers["/a"] = WRONG

    assert verified(environment).language.problems == ()


def test_a_starter_that_hangs_fails_d1(environment, app):
    app.answers["/a"] = ExchangeFailed(ExchangeFailure.TIMED_OUT, "no answer")

    problems = verified(environment).language.problems

    assert any("starter" in problem for problem in problems)


def test_an_app_that_never_starts_fails_d1_and_d3(environment, engine):
    engine.start_error = StackStartError(StartupFailure.APP_EXITED, "your app exited")

    result = verified(environment)

    assert any("does not start" in problem for problem in result.language.problems)
    assert not result.suite.passed


def test_a_failing_test_command_fails_d9(environment, engine):
    engine.exec_outcome = CommandOutcome(1, "1 failing\n")

    result = verified(environment)

    assert not result.suite.passed
    assert "1 failing" in result.suite.failures[0]


def test_a_starters_test_command_that_fails_passes_d1(environment, engine):
    engine.exec_outcome = CommandOutcome(1, "1 failing\n")

    assert verified(environment).language.problems == ()


def test_a_starters_test_command_that_cannot_run_fails_d1(environment, engine):
    engine.exec_outcome = CommandOutcome(127, "node: not found\n")

    assert any("did not run" in problem for problem in verified(environment).language.problems)


def test_a_bootstrap_that_cannot_run_twice_fails_d11(environment, engine):
    engine.one_off_outcome = CommandOutcome(1, "already there\n")

    problems = verified(environment).d11_problems

    assert any("twice" in problem for problem in problems)


def test_egress_fails_d11(environment, engine):
    engine.probe_outcome = CommandOutcome(1, "reached [('1.1.1.1', 443)]\n")

    assert any("1.1.1.1" in problem for problem in verified(environment).d11_problems)


def test_a_case_past_half_its_hang_guard_fails_d11(environment, app):
    app.answers["/a"] = HttpResponse(200, {}, b'{"ok": true}', 6_000_000_000)

    assert any("half" in problem for problem in verified(environment).d11_problems)


def test_verdicts_that_differ_across_runs_fail_d11(environment, app, monkeypatch):
    answers = iter([RIGHT, RIGHT, WRONG, RIGHT, WRONG, RIGHT, RIGHT, WRONG, RIGHT, RIGHT])
    monkeypatch.setattr(app, "send", lambda _request, _limit: next(answers))

    assert any("differ" in problem for problem in verified(environment).d11_problems)


def test_an_install_far_from_its_declared_size_fails_d11(environment, engine, tmp_path):
    def smaller() -> None:
        plan = engine.called("install")[-1]
        folder = Path(plan.paths.project) / "node_modules"
        folder.mkdir(exist_ok=True)
        (folder / "package").write_bytes(b"1")

    engine.after_install = smaller

    assert any("install_mb" in problem for problem in verified(environment).d11_problems)


def test_a_sandbox_that_fails_raises_since_it_says_nothing_about_the_problem(environment, engine):
    engine.start_error = StackStartError(StartupFailure.SERVICE, "not your code")

    with pytest.raises(SandboxError):
        verified(environment)


@pytest.fixture(params=[TYPESCRIPT, PYTHON], ids=["typescript", "python"])
def fixture_problem(request, tmp_path, engine):
    root = make_content(tmp_path)
    copy_fixture(request.param, root / "problems" / request.param)
    return make_environment(root, sandbox=engine), request.param.partition("-")[2]


def report_of(environment, slug: str, **fields: Any):
    request = VerifyRequest(slugs=(slug,), **fields)
    return verify_content(environment, request, lambda _line: None)


def test_the_fixtures_pass_every_static_check(fixture_problem):
    environment, slug = fixture_problem

    report = report_of(environment, slug, static_only=True, require_ready=True)

    assert report.problems[0].static_errors == ()
    assert report.problems[0].ready_errors == ()


def test_static_checks_ask_the_engine_nothing(fixture_problem, engine):
    environment, slug = fixture_problem

    report_of(environment, slug, static_only=True)

    assert engine.calls == []


def test_no_docker_skips_it_with_the_reason(fixture_problem, engine):
    environment, slug = fixture_problem
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    problem = report_of(environment, slug).problems[0]

    assert problem.languages[0].skipped is not None
    assert "Docker" in problem.languages[0].skipped


def test_the_ready_gate_counts_a_skip_as_not_passed(fixture_problem, engine):
    environment, slug = fixture_problem
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    problem = report_of(environment, slug, require_ready=True).problems[0]

    assert any("skipped" in error for error in problem.ready_errors)
