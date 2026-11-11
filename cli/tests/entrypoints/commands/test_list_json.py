"""The filters and `--json` of `cstudy list` (docs/specs/cli.md#cstudy-list)."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["list", *arguments])


def listed_slugs(*arguments: str) -> list[str]:
    return [line.split()[1] for line in invoke(*arguments).output.splitlines()[1:]]


def document(*arguments: str):
    return json.loads(invoke("--json", *arguments).stdout)


def entry(slug: str, *arguments: str):
    return next(found for found in document(*arguments)["entries"] if found["slug"] == slug)


def test_without_a_kind_problems_come_before_items(environment):
    assert listed_slugs() == [
        "two-sum",
        "lru-cache",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_a_kind_of_problem_leaves_the_items_out(environment):
    assert listed_slugs("--kind", "function") == ["two-sum"]


def test_the_item_kind_lists_the_items_only(environment):
    assert listed_slugs("--kind", "item") == ["url-shortener", "news-feed", "retry-wrapper"]


def test_an_unknown_kind_is_a_usage_error(environment):
    assert invoke("--kind", "puzzle").exit_code != 0


def test_a_domain_lists_the_problems_and_items_that_name_it(environment):
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
        "id": "0001",
        "slug": "two-sum",
        "title": "Two Sum",
        "track": "dsa",
        "kind": "function",
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


def test_json_describes_an_item(environment):
    assert entry("url-shortener") == {
        "id": None,
        "slug": "url-shortener",
        "title": "URL Shortener",
        "track": "system-design",
        "kind": "item",
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


def test_json_names_a_workspace_problem_as_yours(environment, monkeypatch):
    workspace_problems = FsProblemRepository(environment.root).over(environment.root)
    yours = replace(environment, problems=workspace_problems)
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: yours)
    assert entry("lru-cache")["source"] == "workspace"


def test_json_applies_the_filters(environment):
    assert [found["slug"] for found in document("--kind", "item")["entries"]] == [
        "url-shortener",
        "news-feed",
        "retry-wrapper",
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
    assert listed_slugs("--search", "two", "--kind", "item") == []


def test_a_search_nothing_holds_says_so(environment):
    assert "no problems match" in invoke("--search", "zebra").output
