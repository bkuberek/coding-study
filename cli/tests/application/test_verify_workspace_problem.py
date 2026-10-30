"""A problem the user wrote in the workspace lists the languages the user picks, not all six."""

import shutil
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import OverlayProblemFiles, OverlayProblemRepository
from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.problem import Language
from tests.e2e import e2e_environment
from tests.fakes import repository_root
from tests.helpers import SCHEMAS_DIRECTORY

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
OWN = "problems/5001-two-sum"


@pytest.fixture
def catalog(tmp_path: Path) -> Path:
    root = tmp_path / "catalog"
    root.mkdir()
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas")
    return root


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """The practice two-sum, renumbered into a workspace's own problems/."""
    root = repository_root(tmp_path / "workspace", PRACTICE)
    (root / "problems" / "0001-two-sum").rename(root / OWN)
    meta = root / OWN / "meta.yaml"
    meta.write_text(meta.read_text().replace('id: "0001"', 'id: "5001"'))
    return root


def edit_meta(workspace: Path, old: str, new: str) -> None:
    meta = workspace / OWN / "meta.yaml"
    meta.write_text(meta.read_text().replace(old, new))


def verified(catalog: Path, workspace: Path, **fields):
    own = FsProblemRepository(catalog)
    environment = e2e_environment(
        workspace,
        content_root=catalog,
        problems=OverlayProblemRepository(own, workspace),
        files=OverlayProblemFiles(FsProblemFiles(catalog), workspace),
    )
    request = VerifyRequest(slugs=("two-sum",), require_ready=True, **fields)
    return verify_content(environment, request, lambda _line: None).problems[0]


def test_a_workspace_problem_listing_python_passes_the_static_checks(catalog, workspace):
    edit_meta(workspace, "track: dsa\n", "track: dsa\nlanguages: [python]\n")
    assert verified(catalog, workspace, static_only=True).static_errors == ()


def test_a_workspace_problem_listing_python_needs_references_in_python_only(catalog, workspace):
    edit_meta(workspace, "track: dsa\n", "track: dsa\nlanguages: [python]\n")
    problem = verified(catalog, workspace, language=Language.PYTHON)
    assert [error for error in problem.ready_errors if "reference" in error] == []


def test_a_workspace_problem_without_languages_needs_the_core_languages(catalog, workspace):
    problem = verified(catalog, workspace, language=Language.PYTHON)
    assert "has no reference in typescript, java, kotlin" in " ".join(problem.ready_errors)
