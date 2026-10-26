"""A workspace's own problems overlaid on the catalog (docs/specs/installation-and-workspaces.md
#your-own-problems)."""

import json
import shutil
from pathlib import Path

import pytest

from coding_study.adapters.document_index import DocumentIndex
from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import OverlayProblemFiles, OverlayProblemRepository
from coding_study.domain.errors import ContentError
from tests.helpers import FIXTURE_PROBLEMS

TWO_SUM = FIXTURE_PROBLEMS / "0001-two-sum"


def own_problem(workspace: Path, directory_name: str, title: str) -> Path:
    """A copy of the two-sum fixture under the workspace's problems/, renamed and retitled."""
    problem_id, _, slug = directory_name.partition("-")
    target = workspace / "problems" / directory_name
    shutil.copytree(TWO_SUM, target)
    meta = (target / "meta.yaml").read_text()
    meta = meta.replace('id: "0001"', f'id: "{problem_id}"').replace(
        "slug: two-sum", f"slug: {slug}"
    )
    (target / "meta.yaml").write_text(meta.replace("title: Two Sum", f"title: {title}"))
    (target / "problem.md").write_text(f"# {title}\n")
    return target


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    own_problem(workspace, "5001-pair-sum", "Pair Sum")
    return workspace


@pytest.fixture
def problems(content_root: Path, workspace: Path) -> OverlayProblemRepository:
    return OverlayProblemRepository(FsProblemRepository(content_root), workspace)


@pytest.fixture
def files(content_root: Path, workspace: Path) -> OverlayProblemFiles:
    return OverlayProblemFiles(FsProblemFiles(content_root), workspace)


def slugs_listed(problems: OverlayProblemRepository) -> list[str]:
    return [summary.meta.slug for summary in problems.list_summaries()]


def test_the_catalog_lists_the_workspace_problems_after_the_catalog_ones(problems):
    assert slugs_listed(problems) == ["two-sum", "lru-cache", "pair-sum"]


def test_a_workspace_problem_loads_from_the_workspace(problems):
    assert problems.load("pair-sum").meta.title == "Pair Sum"


def test_a_workspace_problem_hides_the_catalog_problem_with_its_slug(problems, workspace):
    own_problem(workspace, "0001-two-sum", "My Two Sum")
    assert problems.load("two-sum").meta.title == "My Two Sum"


def test_a_hidden_catalog_problem_is_listed_once(problems, workspace):
    own_problem(workspace, "0001-two-sum", "My Two Sum")
    assert slugs_listed(problems) == ["two-sum", "lru-cache", "pair-sum"]


def test_the_listing_shows_the_workspace_version_of_a_hidden_problem(problems, workspace):
    own_problem(workspace, "0001-two-sum", "My Two Sum")
    assert problems.list_summaries()[0].meta.title == "My Two Sum"


def test_an_id_shared_by_two_slugs_keeps_both_problems(problems, workspace):
    own_problem(workspace, "0001-pair-sum-again", "Pair Sum Again")
    assert slugs_listed(problems) == ["pair-sum-again", "two-sum", "lru-cache", "pair-sum"]


def test_invalid_workspace_problems_are_reported_by_their_workspace_path(problems, workspace):
    (workspace / "problems" / "5001-pair-sum" / "meta.yaml").write_text("id: [\n")
    with pytest.raises(ContentError, match=r"problems/5001-pair-sum/meta\.yaml"):
        problems.list_summaries()


def test_a_listing_keeps_the_index_entries_of_both_layers(content_root, workspace):
    index_file = workspace / ".cs" / "index.json"
    repository = FsProblemRepository(content_root, index=DocumentIndex(index_file))
    OverlayProblemRepository(repository, workspace).list_summaries()
    entries = json.loads(index_file.read_text())["entries"]
    assert len(entries) == 3


def test_problem_files_list_both_layers_in_directory_order(files):
    assert files.slugs() == ("two-sum", "lru-cache", "pair-sum")


def test_problem_files_names_follow_the_slugs(files):
    assert files.directory_names() == ("0001-two-sum", "0002-lru-cache", "5001-pair-sum")


def test_problem_files_resolve_a_workspace_problem_in_the_workspace(files, workspace):
    expected = workspace / "problems" / "5001-pair-sum" / "problem.md"
    assert files.path("pair-sum", "problem.md") == expected


def test_problem_files_hide_the_catalog_directory_of_a_shadowed_slug(files, workspace):
    own_problem(workspace, "0001-two-sum", "My Two Sum")
    assert files.read_text("two-sum", "problem.md") == "# My Two Sum\n"


def test_a_shadowed_slug_is_listed_once(files, workspace):
    own_problem(workspace, "0001-two-sum", "My Two Sum")
    assert files.slugs() == ("two-sum", "lru-cache", "pair-sum")
