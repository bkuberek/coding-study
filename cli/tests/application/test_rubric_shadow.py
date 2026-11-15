"""A problem of your own wins over a catalog rubric problem with its slug, as over any catalog
problem (docs/specs/compatibility.md#rubric-checked-problems)."""

import shutil
from pathlib import Path

import pytest

from coding_study.adapters.fs_item_repository import FsItemRepository
from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import (
    OverlayItemRepository,
    OverlayProblemFiles,
    OverlayProblemRepository,
)
from coding_study.application.environment import Environment
from coding_study.application.list_items import list_items
from coding_study.application.list_problems import ProblemFilter, list_problems
from coding_study.application.practice_catalog import is_item
from coding_study.application.verify_content import VerifyRequest, verify_content
from tests.e2e import e2e_environment
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS, SCHEMAS_DIRECTORY

PRACTICE_TWO_SUM = (
    Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems" / "two-sum"
)

SHADOWED = "url-shortener"


@pytest.fixture
def catalog(tmp_path: Path) -> Path:
    root = tmp_path / "catalog"
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas")
    shutil.copytree(FIXTURE_RUBRIC_PROBLEMS, root / "problems")
    return root


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas")
    return root


def write_autograded(workspace: Path, slug: str) -> None:
    """The practice two-sum, as a problem of your own named `slug`."""
    target = workspace / "problems" / slug
    shutil.copytree(PRACTICE_TWO_SUM, target)
    meta = target / "meta.yaml"
    meta.write_text(meta.read_text().replace("slug: two-sum", f"slug: {slug}"))


def write_rubric(workspace: Path, slug: str) -> None:
    shutil.copytree(FIXTURE_RUBRIC_PROBLEMS / slug, workspace / "problems" / slug)


def overlaid(catalog: Path, workspace: Path) -> Environment:
    return e2e_environment(
        workspace,
        content_root=catalog,
        problems=OverlayProblemRepository(FsProblemRepository(catalog), workspace),
        files=OverlayProblemFiles(FsProblemFiles(catalog), workspace),
        items=OverlayItemRepository(FsItemRepository(catalog), workspace),
    )


def verified(environment: Environment, *slugs: str, **fields):
    request = VerifyRequest(slugs=slugs, static_only=True, **fields)
    return verify_content(environment, request, lambda _line: None).problems


def test_a_problem_of_your_own_is_not_a_rubric_problem(catalog, workspace):
    write_autograded(workspace, SHADOWED)
    environment = overlaid(catalog, workspace)
    assert (is_item(environment, SHADOWED), is_item(environment, "retry-wrapper")) == (False, True)


def test_the_listing_shows_the_shadowing_slug_once(catalog, workspace):
    write_autograded(workspace, SHADOWED)
    environment = overlaid(catalog, workspace)
    everything = ProblemFilter()
    rows = [
        *(listed.summary.meta.slug for listed in list_problems(environment, everything)),
        *(listed.meta.slug for listed in list_items(environment, everything)),
    ]
    assert rows.count(SHADOWED) == 1


def test_the_shadowing_problem_is_the_one_listed(catalog, workspace):
    write_autograded(workspace, SHADOWED)
    environment = overlaid(catalog, workspace)
    listed = {row.summary.meta.slug for row in list_problems(environment, ProblemFilter())}
    assert SHADOWED in listed


def test_verify_checks_the_workspace_problem_not_the_catalog_one(catalog, workspace):
    write_autograded(workspace, SHADOWED)
    problems = verified(overlaid(catalog, workspace), SHADOWED)
    assert [(problem.directory, problem.passed) for problem in problems] == [
        (f"problems/{SHADOWED}", True)
    ]


def test_verify_reports_no_conflict_for_a_shadowed_slug(catalog, workspace):
    write_autograded(workspace, SHADOWED)
    problems = verified(overlaid(catalog, workspace))
    assert [problem.static_errors for problem in problems if SHADOWED in problem.directory] == [()]


def test_verify_refuses_a_rubric_problem_in_the_workspace(catalog, workspace):
    write_rubric(workspace, SHADOWED)
    (problem,) = verified(overlaid(catalog, workspace), SHADOWED)
    assert "rubric problems are catalog-only" in " ".join(problem.static_errors)


def test_a_whole_catalog_verify_refuses_a_rubric_problem_in_the_workspace(catalog, workspace):
    write_rubric(workspace, SHADOWED)
    problems = verified(overlaid(catalog, workspace))
    failing = [problem.directory for problem in problems if problem.static_errors]
    assert failing == [f"problems/{SHADOWED}"]
