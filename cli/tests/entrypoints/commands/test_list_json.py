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
from coding_study.application.problem_sets import add_to_set, create_set
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.config import Config, ProfileSettings
from coding_study.domain.content_ids import ContentType
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems
from coding_study.entrypoints.shared import ExitCode
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


def json_slugs(*arguments: str) -> list[str]:
    return [found["slug"] for found in document(*arguments)["entries"]]


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
        "checked_by": ["rubric", "ai-review"],
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
    } == {"url-shortener": ["rubric", "ai-review"], "news-feed": ["rubric", "ai-review"]}


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


def test_checked_by_ai_review_lists_the_rubric_problems_only(with_a_rubric):
    assert listed_slugs("--checked-by", "ai-review") == [
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


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
    assert invoke("--checked-by", "oracle").exit_code != 0


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


def with_profile(monkeypatch, environment, languages=None, **settings):
    """The environment under a config whose `[profile]` holds `settings`, in a workspace that
    lists `languages` (None: it chose none)."""
    profiled = replace(
        environment,
        config=Config(profile=ProfileSettings(**settings)),
        workspace_languages=languages,
    )
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: profiled)
    monkeypatch.setattr(list_problems, "load_environment", lambda *_: profiled)
    return profiled


NOT_NARROWED = {
    "languages": None,
    "job_roles": None,
    "domains": None,
    "hidden": {"problems": 0},
}


def test_without_a_profile_the_document_names_nothing_hidden(environment):
    assert document()["profile"] == NOT_NARROWED


def test_a_domain_profile_lists_what_names_one_of_its_domains(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("backend",))
    assert json_slugs() == ["lru-cache", "url-shortener", "news-feed", "retry-wrapper"]
    assert document()["profile"] == {
        **NOT_NARROWED,
        "domains": ["backend"],
        "hidden": {"problems": 1},
    }


def test_a_role_profile_keeps_general_and_the_rubric_problems_of_its_roles(
    environment, monkeypatch
):
    with_profile(monkeypatch, environment, job_roles=("platform",))
    assert json_slugs() == ["two-sum", "lru-cache", "url-shortener", "news-feed"]
    assert document()["profile"]["job_roles"] == ["platform"]
    assert document()["profile"]["hidden"] == {"problems": 1}


def test_a_language_profile_keeps_the_rubric_problems(environment, monkeypatch):
    with_profile(monkeypatch, environment, languages=(Language.GO,))
    assert json_slugs() == ["url-shortener", "news-feed", "retry-wrapper"]
    assert document()["profile"] == {**NOT_NARROWED, "languages": ["go"], "hidden": {"problems": 2}}


def test_a_profile_that_hides_nothing_still_names_what_narrowed(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("algorithms", "backend"))
    assert document()["profile"] == {**NOT_NARROWED, "domains": ["algorithms", "backend"]}


@pytest.mark.parametrize("widening", ["domain", "all"])
def test_widen_drops_the_profile_for_the_run(environment, monkeypatch, widening):
    with_profile(monkeypatch, environment, domains=("security",))
    assert json_slugs() == []
    assert len(json_slugs("--widen", widening)) == 5
    assert document("--widen", widening)["profile"] == NOT_NARROWED


def test_widen_of_another_dimension_keeps_the_profile(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("security",))
    assert json_slugs("--widen", "lang", "--widen", "role") == []


def test_widen_repeats_and_takes_each_dimension(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("security",), job_roles=("platform",))
    profile = document("--widen", "role")["profile"]
    assert (profile["domains"], profile["job_roles"]) == (["security"], None)
    assert document("--widen", "role", "--widen", "domain")["profile"] == NOT_NARROWED


def test_an_explicit_filter_replaces_the_profile_in_its_dimension(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("security",), job_roles=("platform",))
    found = document("--domain", "algorithms")
    assert [row["slug"] for row in found["entries"]] == ["two-sum", "lru-cache"]
    assert found["profile"]["domains"] is None
    assert found["profile"]["job_roles"] == ["platform"]


def test_an_explicit_role_matches_without_general_and_leaves_the_profile_there(
    environment, monkeypatch
):
    with_profile(monkeypatch, environment, job_roles=("platform",))
    assert json_slugs("--role", "backend") == [
        "lru-cache",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]
    assert document("--role", "backend")["profile"] == NOT_NARROWED


def test_an_explicit_language_replaces_the_profile_languages(environment, monkeypatch):
    with_profile(monkeypatch, environment, languages=(Language.GO,))
    assert json_slugs("--lang", "python") == ["two-sum", "lru-cache"]
    assert document("--lang", "python")["profile"]["languages"] is None


def test_a_set_ignores_the_profile(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("security",))
    create_set(environment, "mine")
    add_to_set(environment, "mine", ["two-sum", "news-feed"])
    assert json_slugs("--set", "mine") == ["two-sum", "news-feed"]
    assert document("--set", "mine")["profile"] == NOT_NARROWED


def test_widen_must_name_a_dimension_or_all(environment):
    refused = invoke("--widen", "everything")
    assert refused.exit_code == ExitCode.USAGE_ERROR
    assert 'unknown widening "everything"; use lang, role, domain or all' in refused.output


def test_the_profile_line_ends_the_table_and_the_json_has_none(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("backend",))
    lines = invoke().output.splitlines()
    assert lines[-1] == (
        "filtered by your profile: 4 of 5 problems · domains backend · --widen all shows all 5"
    )
    assert lines.count(lines[-1]) == 1
    assert "filtered by" not in invoke("--json").stdout


def test_the_profile_line_counts_the_rows_the_other_filters_keep(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("backend",))
    assert invoke("--search", "sum").output.splitlines() == [
        "no problems match",
        "filtered by your profile: 0 of 1 problems · domains backend · --widen all shows all 1",
    ]


def test_the_profile_line_names_the_narrowed_dimensions_in_order(environment, monkeypatch):
    with_profile(
        monkeypatch,
        environment,
        languages=(Language.PYTHON, Language.GO),
        job_roles=("platform",),
        domains=("backend",),
    )
    assert invoke().output.splitlines()[-1] == (
        "filtered by your profile: 3 of 5 problems · languages python, go"
        " · roles platform and general · domains backend · --widen all shows all 5"
    )


def test_the_profile_line_leaves_out_a_dimension_a_flag_replaced(environment, monkeypatch):
    with_profile(monkeypatch, environment, job_roles=("platform",), domains=("security",))
    assert invoke("--domain", "backend").output.splitlines()[-1] == (
        "filtered by your profile: 3 of 4 problems · roles platform and general"
        " · --widen all shows all 4"
    )


def test_no_line_when_the_profile_hid_nothing_or_was_widened(environment, monkeypatch):
    with_profile(monkeypatch, environment, domains=("algorithms", "backend"))
    assert "filtered by" not in invoke().output
    with_profile(monkeypatch, environment, domains=("security",))
    assert "filtered by" not in invoke("--widen", "all").output
