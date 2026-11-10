"""A service project from `cstudy start` to the last `cstudy submit`, in TypeScript and in Python,
on a real Docker engine. Run with `uv run pytest -q -m docker`. The waits are generous for a busy
machine: what these tests assert is what happened, not how fast."""

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from tests.helpers import SCHEMAS_DIRECTORY
from tests.real_service_projects import (
    MEMBERS,
    PYTHON,
    TYPESCRIPT,
    FixtureProject,
    docker,
    fixture_project,
)

pytestmark = [pytest.mark.slow, pytest.mark.docker]

EXIT_OK = 0
EXIT_FAILURES = 1


@pytest.fixture(scope="module", autouse=True)
def require_engine() -> None:
    try:
        if docker("info", "--format", "{{.ServerVersion}}").returncode != 0:
            pytest.skip("no running Docker engine")
    except FileNotFoundError:
        pytest.skip("no docker on PATH")


@pytest.fixture(params=[TYPESCRIPT, PYTHON], ids=["typescript", "python"])
def project(request: pytest.FixtureRequest, tmp_path: Path) -> Generator[FixtureProject]:
    found = fixture_project(request.param, tmp_path)
    try:
        yield found
    finally:
        found.remove_all_it_left()


def said(result) -> str:
    return f"exit {result.returncode}\n{result.stdout}\n{result.stderr}"


def nothing_running(project: FixtureProject) -> None:
    assert project.labelled("containers") == []
    assert project.labelled("networks") == []


def test_a_project_from_start_to_the_last_level(project: FixtureProject):
    assert_passes_its_static_checks(project)
    assert_start_installs_and_starts_nothing(project)
    assert_the_starter_fails_its_visible_cases(project)
    project.use_naive()
    assert_the_naive_solution_passes_what_is_visible(project)
    assert_the_first_level_opens_the_next(project)
    assert_a_hidden_case_catches_the_naive_solution(project)
    project.use_reference()
    assert_the_reference_finishes_every_level(project)


def assert_passes_its_static_checks(project: FixtureProject) -> None:
    result = project.cstudy("verify", project.slug, "--static")

    assert result.returncode == EXIT_OK, said(result)


def assert_start_installs_and_starts_nothing(project: FixtureProject) -> None:
    result = project.cstudy("start", project.slug, "--yes", "--no-open")

    assert result.returncode == EXIT_OK, said(result)
    assert "cstudy dev" in result.stdout
    assert any(project.folder.glob("node_modules")) or any(project.folder.glob(".venv"))
    nothing_running(project)


def assert_the_starter_fails_its_visible_cases(project: FixtureProject) -> None:
    result = project.cstudy("test")

    assert result.returncode == EXIT_FAILURES, said(result)
    assert "commands.test passed" in result.stdout
    assert "not counted" in result.stdout
    nothing_running(project)


def assert_the_naive_solution_passes_what_is_visible(project: FixtureProject) -> None:
    result = project.cstudy("test")

    assert result.returncode == EXIT_OK, said(result)
    assert "2/2 visible passed" in result.stdout


def assert_the_first_level_opens_the_next(project: FixtureProject) -> None:
    result = project.cstudy("submit")

    assert result.returncode == EXIT_OK, said(result)
    assert "level 2 unlocked" in result.stdout
    nothing_running(project)


def assert_a_hidden_case_catches_the_naive_solution(project: FixtureProject) -> None:
    result = project.cstudy("submit")

    assert result.returncode == EXIT_FAILURES, said(result)
    assert "h5" in result.stdout
    assert "expected 2 requests" in result.stdout
    nothing_running(project)


def assert_the_reference_finishes_every_level(project: FixtureProject) -> None:
    result = project.cstudy("submit")

    assert result.returncode == EXIT_OK, said(result)
    assert "startup" in result.stdout
    nothing_running(project)


@pytest.fixture
def typescript(tmp_path: Path) -> Generator[FixtureProject]:
    found = fixture_project(TYPESCRIPT, tmp_path)
    try:
        yield found
    finally:
        found.remove_all_it_left()


def test_test_events_stream_the_stack_the_command_and_the_visible_cases(
    typescript: FixtureProject,
):
    """`cstudy test --events`, as the Web UI starts it, on the starter: the stack's stages up to
    down, `commands.test` as one test, each visible case, and nothing left running."""
    assert typescript.cstudy("start", typescript.slug, "--yes", "--no-open").returncode == EXIT_OK

    result = typescript.cstudy("test", "--events")

    events: list[dict[str, Any]] = [json.loads(line) for line in result.stdout.splitlines()]
    validator = Draft202012Validator(
        json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
    )
    for event in events:
        validator.validate(event)
    stages = [event["stack"] for event in events if "stack" in event]
    assert stages[-3:] == ["starting", "ready", "stopped"], said(result)
    tests = [event["id"] for event in events if event["type"] == "test_result"]
    assert tests == ["commands.test"]
    assert [event["type"] for event in events].count("case_result") == 2
    assert (events[-1]["type"], events[-1]["exit_code"]) == ("run_end", EXIT_FAILURES)
    assert result.returncode == EXIT_FAILURES
    nothing_running(typescript)


def test_verify_require_ready_passes_on_the_reference(project: FixtureProject):
    result = project.cstudy("verify", project.slug, "--require-ready")

    assert result.returncode == EXIT_OK, said(result)
    nothing_running(project)


@pytest.fixture
def members(tmp_path: Path) -> Generator[FixtureProject]:
    """Postgres and Redis as backing services, migrations, `grade_setup` and `reset`."""
    found = fixture_project(MEMBERS, tmp_path)
    try:
        yield found
    finally:
        found.remove_all_it_left()


def no_data_of_a_run_left(project: FixtureProject) -> None:
    """A test or graded stack's volumes, its backing services' among them, go with it; the install
    cache stays by design."""
    left = [
        volume
        for kind in ("test", "graded")
        for volume in docker(
            "volume",
            "ls",
            "-q",
            "--filter",
            f"label=cstudy.slug={project.slug}",
            "--filter",
            f"label=cstudy.kind={kind}",
        ).stdout.split()
    ]
    assert left == []


def test_a_project_with_postgres_and_redis_from_start_to_the_last_level(members: FixtureProject):
    assert_passes_its_static_checks(members)
    assert_start_installs_and_starts_nothing(members)
    assert_the_starter_fails_its_visible_cases(members)
    members.use_naive()
    assert_the_naive_solution_passes_what_is_visible(members)
    assert_a_member_loaded_before_the_migration_catches_the_naive_one(members)
    members.use_reference()
    assert_the_first_level_opens_the_next(members)
    assert_the_reference_finishes_every_level(members)
    no_data_of_a_run_left(members)


def assert_a_member_loaded_before_the_migration_catches_the_naive_one(
    project: FixtureProject,
) -> None:
    """`grade_setup` loads member 900 into the baseline, and the naive migration drops the table."""
    result = project.cstudy("submit")

    assert result.returncode == EXIT_FAILURES, said(result)
    assert "h3" in result.stdout
    nothing_running(project)
    no_data_of_a_run_left(project)


def test_verify_require_ready_passes_on_the_reference_with_backing_services(
    members: FixtureProject,
):
    result = members.cstudy("verify", members.slug, "--require-ready")

    assert result.returncode == EXIT_OK, said(result)
    nothing_running(members)
    no_data_of_a_run_left(members)
