"""The filters and `--json` of `cstudy list` (docs/specs/cli.md#cstudy-list)."""

import json
import shutil
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import OverlayProblemRepository
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.content_ids import ContentType
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems
from tests.content_id_checks import content_ids_in
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS))
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["list", *arguments])


def listed_slugs(*arguments: str) -> list[str]:
    return [line.split()[0] for line in invoke(*arguments).output.splitlines()[1:]]


def document(*arguments: str):
    return json.loads(invoke("--json", *arguments).stdout)


def entry(slug: str, *arguments: str):
    return next(found for found in document(*arguments)["entries"] if found["slug"] == slug)


def test_without_a_kind_rubric_problems_list_by_track_after_the_problems_before_them(environment):
    assert listed_slugs() == [
        "two-sum",
        "lru-cache",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_a_kind_of_problem_leaves_the_rubric_problems_out(environment):
    assert listed_slugs("--kind", "function") == ["two-sum"]


def test_a_rubric_kind_lists_its_problems_only(environment):
    assert listed_slugs("--kind", "system-design") == ["url-shortener", "news-feed"]
    assert listed_slugs("--kind", "code-review") == ["retry-wrapper"]


def test_the_item_kind_is_gone(environment):
    assert invoke("--kind", "item").exit_code != 0


def test_an_unknown_kind_is_a_usage_error(environment):
    assert invoke("--kind", "puzzle").exit_code != 0


def test_a_domain_lists_the_problems_that_name_it(environment):
    assert listed_slugs("--domain", "backend") == [
        "lru-cache",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_a_role_lists_the_problems_and_items_that_name_it(environment):
    assert listed_slugs("--role", "platform") == ["url-shortener", "news-feed"]


def test_a_scope_lists_the_problems_and_items_of_that_scope(environment):
    assert listed_slugs("--scope", "function") == ["two-sum", "lru-cache", "retry-wrapper"]


def test_the_label_filters_combine_with_each_other_and_with_the_others(environment):
    assert listed_slugs("--domain", "backend", "--role", "general", "--kind", "design") == [
        "lru-cache"
    ]


def test_an_unknown_scope_is_a_usage_error(environment):
    assert invoke("--scope", "galaxy").exit_code != 0


def test_a_label_no_entry_names_matches_nothing(environment):
    assert invoke("--domain", "security").output.strip() == "no problems match"


def test_json_is_dated_today(environment):
    assert document()["today"] == NOW.date().isoformat()


def test_json_lists_problems_then_items(environment):
    assert [found["slug"] for found in document()["entries"]] == [
        "two-sum",
        "lru-cache",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_json_describes_a_problem(environment):
    assert entry("two-sum") == {
        "id": "problem/two-sum",
        "slug": "two-sum",
        "title": "Two Sum",
        "track": "dsa",
        "kind": "function",
        "checked_by": ["tests"],
        "difficulty": "easy",
        "patterns": ["arrays-hashing"],
        "domains": ["algorithms"],
        "job_roles": ["general"],
        "scope": "function",
        "languages": ["python"],
        "content": "ready",
        "source": "catalog",
        "status": "new",
        "levels": None,
        "due_on": None,
        "in_progress": [],
        "jdk": {"min": 21, "max": 26},
        "requires": None,
    }


def test_json_describes_a_rubric_problem(environment):
    assert entry("url-shortener") == {
        "id": "problem/url-shortener",
        "slug": "url-shortener",
        "title": "URL Shortener",
        "track": "system-design",
        "kind": "system-design",
        "checked_by": ["rubric"],
        "difficulty": "medium",
        "patterns": [],
        "domains": ["backend"],
        "job_roles": ["backend", "platform"],
        "scope": "system",
        "languages": [],
        "content": "ready",
        "source": "catalog",
        "status": "new",
        "levels": None,
        "due_on": None,
        "in_progress": [],
        "jdk": None,
        "requires": None,
    }


def test_json_gives_every_entry_its_canonical_id(environment):
    found = content_ids_in(document())
    assert found == [(ContentType.PROBLEM, entry["slug"]) for entry in document()["entries"]]
    assert len(found) == 5


@pytest.fixture
def with_a_rubric(environment, tmp_path):
    """lru-cache, a `design` problem, with a `rubric.md`, as the `lld` problems have one."""
    (tmp_path / "problems" / "lru-cache" / "rubric.md").write_text("# LRU Cache: Rubric\n")


def test_json_says_a_problem_without_a_rubric_is_checked_by_tests(environment):
    assert entry("lru-cache")["checked_by"] == ["tests"]


def test_json_says_a_problem_with_a_rubric_is_checked_by_tests_then_rubric(with_a_rubric):
    assert entry("lru-cache")["checked_by"] == ["tests", "rubric"]


def test_json_says_a_rubric_problem_is_checked_by_its_rubric(environment):
    assert {
        found["slug"]: found["checked_by"]
        for found in document("--kind", "system-design")["entries"]
    } == {"url-shortener": ["rubric"], "news-feed": ["rubric"]}


def test_checked_by_tests_lists_the_problems_with_tests(with_a_rubric):
    assert listed_slugs("--checked-by", "tests") == ["two-sum", "lru-cache"]


def test_checked_by_rubric_lists_the_rubric_problems_and_the_ones_with_a_rubric(with_a_rubric):
    assert listed_slugs("--checked-by", "rubric") == [
        "lru-cache",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_checked_by_rubric_without_a_rubric_in_a_problem_lists_the_rubric_problems_only(
    environment,
):
    assert listed_slugs("--checked-by", "rubric") == ["url-shortener", "news-feed", "retry-wrapper"]


def test_checked_by_combines_with_the_other_filters(with_a_rubric):
    assert listed_slugs("--checked-by", "rubric", "--kind", "design") == ["lru-cache"]
    assert listed_slugs("--checked-by", "tests", "--kind", "system-design") == []


def test_json_applies_checked_by(with_a_rubric):
    assert [found["slug"] for found in document("--checked-by", "rubric")["entries"]] == [
        "lru-cache",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_an_unknown_checked_by_is_a_usage_error(environment):
    assert invoke("--checked-by", "ai-review").exit_code != 0


def test_json_names_each_attempt_in_progress(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.KOTLIN, AttemptMode.NEW, NOW))
    assert entry("two-sum")["in_progress"] == [
        {"attempt_id": 1, "language": "kotlin", "mode": "new"}
    ]


def test_json_names_an_items_attempt_in_progress_without_a_language(environment):
    environment.progress.add_attempt(NewAttempt("url-shortener", None, AttemptMode.REVIEW, NOW))
    assert entry("url-shortener")["in_progress"] == [
        {"attempt_id": 1, "language": None, "mode": "review"}
    ]


def test_json_marks_a_problem_with_an_attempt_in_progress(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.KOTLIN, AttemptMode.NEW, NOW))
    assert entry("two-sum")["status"] == "in_progress"


def test_json_marks_an_item_with_an_attempt_in_progress(environment):
    environment.progress.add_attempt(NewAttempt("url-shortener", None, AttemptMode.NEW, NOW))
    assert entry("url-shortener")["status"] == "in_progress"


def test_json_filters_by_the_in_progress_status(environment):
    environment.progress.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    found = document("--status", "in_progress")["entries"]
    assert [item["slug"] for item in found] == ["two-sum"]


def test_json_has_the_status_and_due_date(environment):
    attempt = environment.progress.add_attempt(
        NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW)
    )
    environment.progress.update_attempt(replace(attempt, status=AttemptStatus.PASSED))
    environment.progress.save_schedule_entry(
        ScheduleEntry("two-sum", ReviewState(interval_days=3), date(2026, 10, 27), Grade.OK, NOW)
    )
    found = entry("two-sum")
    assert (found["status"], found["due_on"]) == ("passed", "2026-10-27")


@pytest.fixture
def yours(environment, tmp_path_factory, monkeypatch):
    """The environment with lru-cache as a problem of the workspace, not of the catalog."""
    workspace = tmp_path_factory.mktemp("workspace")
    shutil.copytree(
        environment.root / "problems" / "lru-cache", workspace / "problems" / "lru-cache"
    )
    shutil.rmtree(environment.root / "problems" / "lru-cache")
    problems = OverlayProblemRepository(FsProblemRepository(environment.root), workspace)
    overlaid = replace(environment, problems=problems)
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: overlaid)
    return overlaid


def test_json_names_a_workspace_problem_as_yours(yours):
    assert entry("lru-cache")["source"] == "workspace"


def test_your_own_problems_list_after_the_catalogs_rubric_problems(yours):
    assert listed_slugs() == ["two-sum", "url-shortener", "news-feed", "retry-wrapper", "lru-cache"]
    assert [found["slug"] for found in document()["entries"]] == [
        "two-sum",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
        "lru-cache",
    ]


def test_json_applies_the_filters(environment):
    assert [found["slug"] for found in document("--kind", "code-review")["entries"]] == [
        "retry-wrapper"
    ]


def test_json_with_no_match_has_no_entries(environment):
    assert document("--lang", "kotlin")["entries"] == []


def test_search_finds_a_word_of_the_slug(environment):
    assert listed_slugs("--search", "lru") == ["lru-cache"]


def test_search_finds_a_word_of_the_title_the_slug_does_not_hold(environment):
    assert listed_slugs("--search", "Two Sum") == ["two-sum"]


def test_search_ignores_case(environment):
    assert listed_slugs("--search", "LRU cache") == ["lru-cache"]


def test_search_ignores_the_spaces_around_it(environment):
    assert listed_slugs("--search", "  lru ") == ["lru-cache"]


def test_search_reads_the_items_too(environment):
    assert listed_slugs("--search", "news") == ["news-feed"]


def test_search_narrows_what_the_other_filters_leave(environment):
    assert listed_slugs("--search", "two", "--kind", "system-design") == []


def test_a_search_nothing_holds_says_so(environment):
    assert "no problems match" in invoke("--search", "zebra").output
