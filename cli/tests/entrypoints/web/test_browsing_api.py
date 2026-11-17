"""The browsing endpoints: each answers the document of the CLI command it mirrors, through the
same use case (docs/specs/web-ui.md#browsing)."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.list_problems import ProblemFilter
from coding_study.application.next_problem import NextRequest, recommend
from coding_study.application.problem_history import problem_history
from coding_study.application.problem_sets import add_to_set, create_set
from coding_study.application.show_statement import ShowRequest, show_statement
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.checked_by import CheckedBy
from coding_study.domain.config import Config, ProfileSettings
from coding_study.domain.content_ids import ContentType
from coding_study.domain.items import EntryKind
from coding_study.domain.labels import LabelFilter
from coding_study.domain.next_selection import NextSource
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.taxonomy import Scope
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems, next_problem
from coding_study.entrypoints.commands.history import history_document
from coding_study.entrypoints.commands.list_problems import list_document
from coding_study.entrypoints.commands.next_problem import next_document
from tests.content_id_checks import content_ids_in
from tests.fakes import (
    FakeStubGenerator,
    FakeToolchains,
    declare_jdk,
    jdk_of,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS, PROJECT_PROBLEMS
from tests.web_server import session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
TOOLCHAINS = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})


@pytest.fixture
def environment(tmp_path):
    return make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS), toolchains=TOOLCHAINS
    )


@pytest.fixture
def client(tmp_path, environment):
    with session_client(web_app(tmp_path, environment)) as client:
        yield client


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


# problems


def test_the_problem_list_is_the_list_document(client, environment):
    assert client.get("/api/v1/problems").json() == list_document(environment, ProblemFilter())


def test_the_problem_list_shows_attempts_in_progress(client, environment):
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    assert client.get("/api/v1/problems").json() == list_document(environment, ProblemFilter())


def test_the_problem_list_filters_by_the_in_progress_status(client, environment):
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    found = client.get("/api/v1/problems?status=in_progress").json()
    assert [entry["slug"] for entry in found["entries"]] == ["two-sum"]


def test_a_started_problem_reads_in_progress_in_the_list(client, environment):
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    entries = client.get("/api/v1/problems").json()["entries"]
    assert {entry["slug"]: entry["status"] for entry in entries}["two-sum"] == "in_progress"


@pytest.mark.parametrize(
    ("query", "problem_filter"),
    [
        ("track=system-design", ProblemFilter(track=Track.SYSTEM_DESIGN)),
        ("kind=system-design", ProblemFilter(kind=EntryKind.SYSTEM_DESIGN)),
        ("kind=design", ProblemFilter(kind=EntryKind.DESIGN)),
        ("difficulty=medium", ProblemFilter(difficulty=Difficulty.MEDIUM)),
        (
            "lang=python&pattern=arrays-hashing",
            ProblemFilter(pattern="arrays-hashing", language=Language.PYTHON),
        ),
        ("status=new&content=ready", ProblemFilter(status="new", content="ready")),  # type: ignore[arg-type]
        ("domain=backend", ProblemFilter(labels=LabelFilter(domain="backend"))),
        ("role=platform", ProblemFilter(labels=LabelFilter(role="platform"))),
        ("scope=function", ProblemFilter(labels=LabelFilter(scope=Scope.FUNCTION))),
        ("checked=rubric", ProblemFilter(checked_by=CheckedBy.RUBRIC)),
        ("checked=tests", ProblemFilter(checked_by=CheckedBy.TESTS)),
        ("checked=ai-review", ProblemFilter(checked_by=CheckedBy.AI_REVIEW)),
        (
            "domain=backend&role=general&scope=function",
            ProblemFilter(labels=LabelFilter("backend", "general", Scope.FUNCTION)),
        ),
    ],
)
def test_the_problem_list_takes_the_filters_of_cstudy_list(
    client, environment, query, problem_filter
):
    expected = list_document(environment, problem_filter)
    assert client.get(f"/api/v1/problems?{query}").json() == expected


def test_an_unknown_filter_value_gets_422_usage(client):
    response = client.get("/api/v1/problems?track=chess")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        'invalid track "chess": use one of dsa, practical, lld, concurrency, debugging, '
        "system-design, code-review, behavioral",
    )


def test_the_problem_list_filters_by_label_as_cstudy_list_does(client):
    entries = client.get("/api/v1/problems?domain=backend&role=general").json()["entries"]
    assert [entry["slug"] for entry in entries] == ["lru-cache"]


def test_an_unknown_scope_gets_422_usage(client):
    response = client.get("/api/v1/problems?scope=galaxy")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        'invalid scope "galaxy": use one of function, project, system',
    )


# one problem


def test_a_problem_is_its_list_entry_with_its_details(client, environment):
    entry = next(
        found
        for found in list_document(environment, ProblemFilter())["entries"]  # type: ignore[union-attr]
        if found["slug"] == "two-sum"  # type: ignore[index]
    )
    document = client.get("/api/v1/problems/two-sum").json()
    assert {key: document[key] for key in entry if key != "languages"} == {  # type: ignore[union-attr]
        key: value
        for key, value in entry.items()  # type: ignore[union-attr]
        if key != "languages"
    }


def test_a_problem_has_its_canonical_id_and_how_it_is_checked(client):
    two_sum = client.get("/api/v1/problems/two-sum").json()
    rubric = client.get("/api/v1/problems/url-shortener").json()
    assert (two_sum["id"], two_sum["checked_by"]) == ("problem/two-sum", ["tests"])
    assert (rubric["id"], rubric["checked_by"]) == (
        "problem/url-shortener",
        ["rubric", "ai-review"],
    )


def test_the_problem_list_gives_each_entry_its_id_and_how_it_is_checked(client):
    entries = client.get("/api/v1/problems").json()["entries"]
    assert content_ids_in(entries) == [(ContentType.PROBLEM, entry["slug"]) for entry in entries]
    assert {entry["slug"]: entry["checked_by"] for entry in entries} == {
        "two-sum": ["tests"],
        "lru-cache": ["tests"],
        "url-shortener": ["rubric", "ai-review"],
        "news-feed": ["rubric", "ai-review"],
        "retry-wrapper": ["rubric", "ai-review"],
    }


def test_a_problem_with_a_rubric_is_checked_by_tests_then_rubric(client, tmp_path):
    (tmp_path / "problems" / "lru-cache" / "rubric.md").write_text("# LRU Cache: Rubric\n")
    assert client.get("/api/v1/problems/lru-cache").json()["checked_by"] == ["tests", "rubric"]
    listed = client.get("/api/v1/problems?checked=rubric").json()["entries"]
    assert [entry["slug"] for entry in listed] == [
        "lru-cache",
        "url-shortener",
        "news-feed",
        "retry-wrapper",
    ]


def test_checked_ai_review_lists_the_rubric_problems_only(client, tmp_path):
    (tmp_path / "problems" / "lru-cache" / "rubric.md").write_text("# LRU Cache: Rubric\n")
    listed = client.get("/api/v1/problems?checked=ai-review").json()["entries"]
    assert [entry["slug"] for entry in listed] == ["url-shortener", "news-feed", "retry-wrapper"]


def test_an_unknown_checked_value_gets_422_usage(client):
    assert error(client.get("/api/v1/problems?checked=oracle")) == (422, "usage")


def test_a_problem_adds_what_its_actions_accept(client):
    document = client.get("/api/v1/problems/two-sum").json()
    assert {
        key: document[key]
        for key in ("approaches", "broken", "levels", "hints_total", "bench", "oracle")
    } == {
        "approaches": [
            {"id": "brute-force", "name": "Check every pair", "role": "brute"},
            {"id": "hash-map", "name": "One-pass hash map", "role": "optimal"},
        ],
        "broken": [],
        "levels": None,
        "hints_total": 2,
        "bench": True,
        "oracle": True,
    }


def test_a_problems_languages_are_those_it_starts_in(client):
    languages = client.get("/api/v1/problems/two-sum").json()["languages"]
    assert languages == [language.value for language in Language]


def test_a_project_names_its_last_level(tmp_path):
    environment = make_environment(repository_root(tmp_path, PROJECT_PROBLEMS))
    with session_client(web_app(tmp_path, environment)) as client:
        document = client.get("/api/v1/problems/bank-project-python").json()
    assert (document["levels"], document["languages"]) == (
        {"last": 2, "passed": 0, "mastered": 0},
        ["python"],
    )


def test_an_item_has_empty_details(client):
    document = client.get("/api/v1/problems/url-shortener").json()
    assert {
        key: document[key]
        for key in (
            "kind",
            "languages",
            "approaches",
            "broken",
            "levels",
            "hints_total",
            "bench",
            "oracle",
        )
    } == {
        "kind": "system-design",
        "languages": [],
        "approaches": [],
        "broken": [],
        "levels": None,
        "hints_total": 0,
        "bench": False,
        "oracle": False,
    }


def test_an_unknown_problem_gets_404_not_found(client):
    assert error(client.get("/api/v1/problems/three-sum")) == (404, "not_found")


# statement


def test_the_statement_is_the_text_cstudy_show_prints(client, environment):
    expected = show_statement(environment, ShowRequest("two-sum"))
    assert client.get("/api/v1/problems/two-sum/statement").json()["markdown"] == expected


def test_the_statement_comes_rendered_as_html(client):
    html = client.get("/api/v1/problems/two-sum/statement").json()["html"]
    assert html.startswith("<h1>Two Sum</h1>")


def test_the_statement_html_leaves_out_the_footer_comment_of_the_statement_file(client):
    document = client.get("/api/v1/problems/two-sum/statement").json()
    assert "Rendered by cstudy" in document["markdown"]
    assert "Rendered by cstudy" not in document["html"]
    assert "<!--" not in document["html"]


def test_the_statement_names_the_jdk_range_the_problem_declares(tmp_path):
    root = repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS)
    declare_jdk(root, "two-sum", "{min: 24}")
    environment = make_environment(root, toolchains=TOOLCHAINS)
    with session_client(web_app(tmp_path, environment)) as client:
        document = client.get("/api/v1/problems/two-sum/statement").json()
    assert "Java and Kotlin: JDK 24 or newer" in document["html"]


def test_the_problem_document_carries_the_range_the_problem_declares(tmp_path):
    root = repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS)
    declare_jdk(root, "two-sum", "{min: 24}")
    environment = make_environment(root, toolchains=TOOLCHAINS)
    with session_client(web_app(tmp_path, environment)) as client:
        document = client.get("/api/v1/problems/two-sum").json()
    assert document["jdk"] == {"min": 24, "max": 26}


def test_an_items_statement_is_the_one_cstudy_show_prints(client, environment):
    expected = show_statement(environment, ShowRequest("url-shortener"))
    assert client.get("/api/v1/problems/url-shortener/statement").json()["markdown"] == expected


def test_a_level_on_a_problem_without_levels_gets_the_clis_422(client, environment):
    response = client.get("/api/v1/problems/url-shortener/statement?level=2")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "url-shortener has no levels",
    )


def test_a_level_that_is_not_a_positive_integer_gets_422(client):
    response = client.get("/api/v1/problems/two-sum/statement?level=0")
    assert error(response) == (422, "usage")


def test_the_statement_of_an_unknown_problem_gets_404(client):
    assert error(client.get("/api/v1/problems/three-sum/statement")) == (404, "not_found")


# history


def test_the_history_is_the_history_document(client, environment):
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    expected = history_document(problem_history(environment, "two-sum"))
    assert client.get("/api/v1/problems/two-sum/history").json() == expected


def test_the_history_of_an_unknown_problem_gets_404(client):
    assert error(client.get("/api/v1/problems/three-sum/history")) == (404, "not_found")


# next


def test_the_next_pick_is_the_next_document(client, environment):
    assert client.get("/api/v1/next").json() == next_document(recommend(environment, NextRequest()))


def test_the_next_pick_resumes_the_attempt_in_progress(client, environment):
    attempt = start_attempt(environment, StartRequest("two-sum", Language.PYTHON)).attempt
    found = client.get("/api/v1/next").json()
    assert (found["pick"], found["slug"], found["attempt_id"], found["also_open"]) == (
        "resume",
        "two-sum",
        attempt.id,
        [],
    )


def test_new_on_the_next_pick_skips_the_attempt_in_progress(client, environment):
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    found = client.get("/api/v1/next?new=true").json()
    forced = next_document(recommend(environment, NextRequest(source=NextSource.NEW_ONLY)))
    assert found == forced
    assert found["pick"] != "resume"


def test_the_next_pick_takes_the_options_of_cstudy_next(client, environment):
    request = NextRequest(
        (Track.DSA, Track.SYSTEM_DESIGN),
        None,
        Difficulty.EASY,
        Language.KOTLIN,
        NextSource.NEW_ONLY,
    )
    query = "track=dsa&track=system-design&difficulty=easy&lang=kotlin&new=true"
    assert client.get(f"/api/v1/next?{query}").json() == next_document(
        recommend(environment, request)
    )


def test_the_next_pick_takes_the_label_filters_of_cstudy_next(client, environment):
    request = NextRequest(labels=LabelFilter(role="platform", scope=Scope.SYSTEM))
    assert client.get("/api/v1/next?role=platform&scope=system").json() == next_document(
        recommend(environment, request)
    )


def test_a_label_filter_on_the_next_pick_searches_every_track(client):
    assert client.get("/api/v1/next?role=platform").json()["slug"] == "url-shortener"


def test_an_unknown_domain_on_the_next_pick_gets_422_usage(client):
    assert error(client.get("/api/v1/next?domain=chess")) == (422, "usage")


UNPROFILED = {"languages": None, "job_roles": None, "domains": None, "hidden": {"problems": 0}}


def test_nothing_to_pick_is_the_clis_message(client):
    assert client.get("/api/v1/next?track=practical").json() == {
        "pick": None,
        "message": "nothing due and no new problems in scope",
        "profile": UNPROFILED,
    }


def test_new_and_review_together_get_the_clis_422(client):
    response = client.get("/api/v1/next?new=true&review=true")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        "--new and --review exclude each other",
    )


def test_a_boolean_that_is_not_true_or_false_gets_422(client):
    assert error(client.get("/api/v1/next?new=yes")) == (422, "usage")


def test_the_next_pick_says_which_jdk_ran_out_of_problems(tmp_path):
    environment = make_environment(repository_root(tmp_path, PRACTICE), jdk=jdk_of(27))
    with session_client(web_app(tmp_path, environment)) as client:
        document = client.get("/api/v1/next?lang=java").json()
    assert document == {
        "pick": None,
        "message": "nothing to pick: JDK 27 (JAVA_HOME) cannot run java problems; "
        "cstudy supports JDK 21 to 26",
        "profile": UNPROFILED,
    }


def test_the_problem_document_carries_the_jdk_range_of_the_listing(client, environment):
    document = client.get("/api/v1/problems/two-sum").json()
    assert document["jdk"] == {"min": 21, "max": 26}


# the learner profile (docs/specs/cli.md#the-learner-profile)

runner = CliRunner()
BACKEND = ProfileSettings(domains=("backend",))


def profiled(environment, languages=None, settings=BACKEND):
    """The workspace under a config whose `[profile]` is `settings`, listing `languages` (None:
    it chose none)."""
    return replace(environment, config=Config(profile=settings), workspace_languages=languages)


@pytest.fixture
def narrowed(tmp_path, environment):
    """A server over a workspace whose profile keeps the backend domain, and that workspace."""
    narrowing = profiled(environment)
    with session_client(web_app(tmp_path, narrowing)) as client:
        yield client, narrowing


def cli_document(monkeypatch, environment, *arguments: str):
    """What the command prints under `--json` in that workspace."""
    for module, names in (
        (list_problems, ("load_catalog_environment", "load_environment")),
        (next_problem, ("load_environment",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, lambda *_: environment)
    result = runner.invoke(cli.app, [*arguments, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def slugs(document) -> list[str]:
    return [entry["slug"] for entry in document["entries"]]


def test_the_problem_list_applies_the_learner_profile(narrowed):
    client, _ = narrowed
    document = client.get("/api/v1/problems").json()
    profile = document["profile"]
    assert (profile["domains"], profile["hidden"]["problems"] > 0) == (["backend"], True)
    assert "two-sum" not in slugs(document)


def test_the_problem_list_is_what_cstudy_list_prints_under_the_profile(narrowed, monkeypatch):
    client, environment = narrowed
    assert client.get("/api/v1/problems").json() == cli_document(monkeypatch, environment, "list")


@pytest.mark.parametrize(
    ("query", "flags"),
    [
        ("widen=all", ["--widen", "all"]),
        ("widen=domain", ["--widen", "domain"]),
        ("widen=role&widen=domain", ["--widen", "role", "--widen", "domain"]),
        ("widen=role", ["--widen", "role"]),
        ("domain=algorithms", ["--domain", "algorithms"]),
        ("lang=go", ["--lang", "go"]),
        ("role=general&widen=lang", ["--role", "general", "--widen", "lang"]),
    ],
)
def test_widening_the_problem_list_is_what_cstudy_list_widen_prints(
    narrowed, monkeypatch, query, flags
):
    client, environment = narrowed
    expected = cli_document(monkeypatch, environment, "list", *flags)
    assert client.get(f"/api/v1/problems?{query}").json() == expected


def test_widening_every_dimension_lists_what_the_profile_hid(narrowed):
    client, _ = narrowed
    document = client.get("/api/v1/problems?widen=all").json()
    assert (document["profile"]["hidden"], "two-sum" in slugs(document)) == (
        {"problems": 0},
        True,
    )


def test_an_explicit_filter_replaces_the_profile_in_its_dimension(narrowed):
    client, _ = narrowed
    document = client.get("/api/v1/problems?domain=algorithms").json()
    assert ("two-sum" in slugs(document), document["profile"]["domains"]) == (True, None)


def test_a_workspaces_languages_narrow_the_list_as_the_profile_does(tmp_path, environment):
    go = profiled(environment, (Language.GO,), ProfileSettings())
    with session_client(web_app(tmp_path, go)) as client:
        document = client.get("/api/v1/problems").json()
    assert document["profile"]["languages"] == ["go"]


def test_a_set_ignores_the_profile(tmp_path, environment):
    narrowing = profiled(environment)
    create_set(narrowing, "loop")
    add_to_set(narrowing, "loop", ["two-sum"])
    with session_client(web_app(tmp_path, narrowing)) as client:
        document = client.get("/api/v1/problems?set=loop").json()
    assert (slugs(document), document["profile"]["hidden"]) == (["two-sum"], {"problems": 0})


def test_an_unknown_widening_gets_the_clis_422(narrowed):
    client, _ = narrowed
    response = client.get("/api/v1/problems?widen=everything")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        'unknown widening "everything"; use lang, role, domain or all',
    )


def test_the_next_pick_applies_the_learner_profile(narrowed, monkeypatch):
    client, environment = narrowed
    document = client.get("/api/v1/next").json()
    assert document == cli_document(monkeypatch, environment, "next")
    assert document["profile"]["domains"] == ["backend"]


@pytest.mark.parametrize(
    ("query", "flags"),
    [
        ("widen=all", ["--widen", "all"]),
        ("widen=domain&widen=role", ["--widen", "domain", "--widen", "role"]),
        ("domain=algorithms", ["--domain", "algorithms"]),
    ],
)
def test_widening_the_next_pick_is_what_cstudy_next_widen_picks(
    narrowed, monkeypatch, query, flags
):
    client, environment = narrowed
    expected = cli_document(monkeypatch, environment, "next", *flags)
    assert client.get(f"/api/v1/next?{query}").json() == expected


def test_the_next_pick_widens_roles_and_domains_only(narrowed):
    client, _ = narrowed
    response = client.get("/api/v1/next?widen=lang")
    assert (error(response), response.json()["error"]["message"]) == (
        (422, "usage"),
        'unknown widening "lang"; use role, domain or all',
    )
