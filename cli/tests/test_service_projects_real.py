"""A service project from `cstudy start` to the last `cstudy submit`, in TypeScript and in Python,
on a real Docker engine. Run with `uv run pytest -q -m docker`. The waits are generous for a busy
machine: what these tests assert is what happened, not how fast."""

from collections.abc import Generator
from pathlib import Path

import pytest

from tests.real_service_projects import (
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


def test_verify_require_ready_passes_on_the_reference(project: FixtureProject):
    result = project.cstudy("verify", project.slug, "--require-ready")

    assert result.returncode == EXIT_OK, said(result)
    nothing_running(project)
