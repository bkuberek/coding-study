"""A workspace's own problems overlaid on the catalog (docs/specs/installation-and-workspaces.md
#your-own-problems)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from coding_study.adapters.document_index import DocumentIndex
from coding_study.adapters.fs_item_repository import FsItemRepository
from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import (
    OverlayItemRepository,
    OverlayProblemFiles,
    OverlayProblemRepository,
)
from coding_study.domain.errors import ContentError, UnknownProblemError
from coding_study.domain.problem import ALL_LANGUAGES, CORE_LANGUAGES
from tests.helpers import FIXTURE_PROBLEMS, FIXTURE_RUBRIC_PROBLEMS, numbered_directory

TWO_SUM = FIXTURE_PROBLEMS / "two-sum"


def own_problem(workspace: Path, slug: str, title: str) -> Path:
    """A copy of the two-sum fixture under the workspace's problems/, renamed and retitled."""
    target = workspace / "problems" / slug
    shutil.copytree(TWO_SUM, target)
    meta = (target / "meta.yaml").read_text().replace("slug: two-sum", f"slug: {slug}")
    (target / "meta.yaml").write_text(meta.replace("title: Two Sum", f"title: {title}"))
    (target / "problem.md").write_text(f"# {title}\n")
    return target


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    own_problem(workspace, "pair-sum", "Pair Sum")
    return workspace


@pytest.fixture
def problems(content_root: Path, workspace: Path) -> OverlayProblemRepository:
    return OverlayProblemRepository(FsProblemRepository(content_root), workspace)


@pytest.fixture
def files(content_root: Path, workspace: Path) -> OverlayProblemFiles:
    return OverlayProblemFiles(FsProblemFiles(content_root), workspace)


def slugs_listed(problems: OverlayProblemRepository) -> list[str]:
    return [summary.meta.slug for summary in problems.list_summaries()]


def test_the_catalog_lists_the_workspace_problems_with_the_catalog_ones_by_slug(problems):
    assert slugs_listed(problems) == ["lru-cache", "pair-sum", "two-sum"]


def test_a_workspace_problem_loads_from_the_workspace(problems):
    assert problems.load("pair-sum").meta.title == "Pair Sum"


def test_a_workspace_problem_hides_the_catalog_problem_with_its_slug(problems, workspace):
    own_problem(workspace, "two-sum", "My Two Sum")
    assert problems.load("two-sum").meta.title == "My Two Sum"


def test_a_hidden_catalog_problem_is_listed_once(problems, workspace):
    own_problem(workspace, "two-sum", "My Two Sum")
    assert slugs_listed(problems) == ["lru-cache", "pair-sum", "two-sum"]


def test_the_listing_shows_the_workspace_version_of_a_hidden_problem(problems, workspace):
    own_problem(workspace, "two-sum", "My Two Sum")
    shown = {summary.meta.slug: summary.meta.title for summary in problems.list_summaries()}
    assert shown["two-sum"] == "My Two Sum"


def test_invalid_workspace_problems_are_reported_by_their_workspace_path(problems, workspace):
    (workspace / "problems" / "pair-sum" / "meta.yaml").write_text("slug: [\n")
    with pytest.raises(ContentError, match=r"problems/pair-sum/meta\.yaml"):
        problems.list_summaries()


def test_a_listing_keeps_the_index_entries_of_both_layers(content_root, workspace):
    index_file = workspace / ".cs" / "index.json"
    repository = FsProblemRepository(content_root, index=DocumentIndex(index_file))
    OverlayProblemRepository(repository, workspace).list_summaries()
    entries = json.loads(index_file.read_text())["entries"]
    assert len(entries) == 3


def test_problem_files_list_both_layers_in_name_order(files):
    assert files.slugs() == ("lru-cache", "pair-sum", "two-sum")


def test_problem_files_report_the_misnamed_directories_of_both_layers(files, workspace):
    name = numbered_directory(5001, "max-gap")
    (workspace / "problems" / name).mkdir()
    assert [found.name for found in files.misnamed()] == [name]


def test_each_misnamed_directory_names_the_root_it_sits_under(files, content_root, workspace):
    (content_root / "problems" / numbered_directory(1, "catalog-one")).mkdir()
    (workspace / "problems" / numbered_directory(2, "own-one")).mkdir()
    assert [found.fix("problems").split(" run")[0] for found in files.misnamed()] == [
        "from the content root",
        "from the workspace root",
    ]


def test_hidden_directories_of_both_layers_are_no_problems(files, content_root, workspace):
    for root in (content_root, workspace):
        (root / "problems" / "__pycache__").mkdir()
        (root / "problems" / ".cache").mkdir()
    assert files.misnamed() == ()


def old_workspace_problem(workspace: Path) -> str:
    """A problem as `cstudy new` wrote it before problem ids went: a numbered folder whose
    meta.yaml has an `id:` line."""
    name = numbered_directory(5001, "max-gap")
    target = own_problem(workspace, "max-gap", "Max Gap")
    target.rename(workspace / "problems" / name)
    meta = workspace / "problems" / name / "meta.yaml"
    meta.write_text("id: '5001'\n" + meta.read_text())
    return name


def test_an_old_workspace_problem_loads_once_the_advice_is_followed(problems, files, workspace):
    name = old_workspace_problem(workspace)
    (found,) = files.misnamed()
    assert found.name == name
    command = found.fix("problems").split("`")[1]
    subprocess.run(command, shell=True, cwd=workspace, check=True)
    with pytest.raises(ContentError, match="id"):
        problems.list_summaries()
    assert [found.name for found in files.misnamed()] == ["max-gap"]
    meta = workspace / "problems" / "max-gap" / "meta.yaml"
    meta.write_text(
        "".join(line for line in meta.read_text().splitlines(True) if line[:3] != "id:")
    )
    assert files.misnamed() == ()
    assert slugs_listed(problems) == ["lru-cache", "max-gap", "pair-sum", "two-sum"]


def test_problem_files_resolve_a_workspace_problem_in_the_workspace(files, workspace):
    expected = workspace / "problems" / "pair-sum" / "problem.md"
    assert files.path("pair-sum", "problem.md") == expected


def test_problem_files_hide_the_catalog_directory_of_a_shadowed_slug(files, workspace):
    own_problem(workspace, "two-sum", "My Two Sum")
    assert files.read_text("two-sum", "problem.md") == "# My Two Sum\n"


def test_a_shadowed_slug_is_listed_once(files, workspace):
    own_problem(workspace, "two-sum", "My Two Sum")
    assert files.slugs() == ("lru-cache", "pair-sum", "two-sum")


def test_a_workspace_problem_without_languages_lists_the_core_languages(problems):
    assert problems.load("pair-sum").meta.languages == CORE_LANGUAGES


def test_a_listing_gives_a_workspace_problem_the_core_languages_too(problems):
    own = next(s for s in problems.list_summaries() if s.meta.slug == "pair-sum")
    assert own.meta.languages == CORE_LANGUAGES


def test_a_workspace_problem_lists_the_languages_it_names(problems, workspace):
    meta = workspace / "problems" / "pair-sum" / "meta.yaml"
    meta.write_text(meta.read_text().replace("track: dsa\n", "track: dsa\nlanguages: [python]\n"))
    assert [language.value for language in problems.load("pair-sum").meta.languages] == ["python"]


def test_a_catalog_problem_without_languages_lists_every_language(problems):
    assert problems.load("two-sum").meta.languages == ALL_LANGUAGES


def test_only_a_workspace_problem_is_marked_as_one(problems):
    assert [(s.meta.slug, s.meta.workspace) for s in problems.list_summaries()] == [
        ("lru-cache", False),
        ("pair-sum", True),
        ("two-sum", False),
    ]


@pytest.fixture
def rubric_content(content_root: Path) -> Path:
    shutil.copytree(FIXTURE_RUBRIC_PROBLEMS, content_root / "problems", dirs_exist_ok=True)
    return content_root


@pytest.fixture
def items(rubric_content: Path, workspace: Path) -> OverlayItemRepository:
    return OverlayItemRepository(FsItemRepository(rubric_content), workspace)


def test_the_catalog_rubric_problems_are_visible_without_a_workspace_problem_of_their_slug(items):
    assert items.slugs() == ("news-feed", "retry-wrapper", "url-shortener")


def test_a_workspace_problem_hides_the_catalog_rubric_problem_with_its_slug(items, workspace):
    own_problem(workspace, "url-shortener", "My URL Shortener")
    assert (items.slugs(), items.contains("url-shortener")) == (
        ("news-feed", "retry-wrapper"),
        False,
    )


def test_a_hidden_rubric_problem_is_not_listed_or_loaded(items, workspace):
    own_problem(workspace, "url-shortener", "My URL Shortener")
    assert [meta.slug for meta in items.list_items()] == ["news-feed", "retry-wrapper"]
    with pytest.raises(UnknownProblemError):
        items.load("url-shortener")


def test_the_directories_follow_the_visible_slugs(items, workspace):
    own_problem(workspace, "news-feed", "My News Feed")
    assert items.directories() == ("problems/retry-wrapper", "problems/url-shortener")
