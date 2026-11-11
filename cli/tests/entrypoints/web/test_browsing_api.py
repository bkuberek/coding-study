"""The browsing endpoints: each answers the document of the CLI command it mirrors, through the
same use case (docs/specs/web-ui.md#browsing)."""

from pathlib import Path

import pytest

from coding_study.application.list_problems import ProblemFilter
from coding_study.application.next_problem import NextRequest, recommend
from coding_study.application.problem_history import problem_history
from coding_study.application.show_statement import ShowRequest, show_statement
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.items import EntryKind
from coding_study.domain.labels import LabelFilter
from coding_study.domain.next_selection import NextSource
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.taxonomy import Scope
from coding_study.entrypoints.commands.history import history_document
from coding_study.entrypoints.commands.list_problems import list_document
from coding_study.entrypoints.commands.next_problem import next_document
from tests.fakes import (
    FakeStubGenerator,
    FakeToolchains,
    declare_jdk,
    jdk_of,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_TRACKS, PROJECT_PROBLEMS
from tests.web_server import session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
TOOLCHAINS = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})


@pytest.fixture
def environment(tmp_path):
    return make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS), toolchains=TOOLCHAINS
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
        ("kind=item", ProblemFilter(kind=EntryKind.ITEM)),
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
        "kind": "item",
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


def test_the_statement_names_the_jdk_range_the_problem_declares(tmp_path):
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    declare_jdk(root, "0001-two-sum", "{min: 24}")
    environment = make_environment(root, toolchains=TOOLCHAINS)
    with session_client(web_app(tmp_path, environment)) as client:
        document = client.get("/api/v1/problems/two-sum/statement").json()
    assert "Java and Kotlin: JDK 24 or newer" in document["html"]


def test_the_problem_document_carries_the_range_the_problem_declares(tmp_path):
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    declare_jdk(root, "0001-two-sum", "{min: 24}")
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


def test_nothing_to_pick_is_the_clis_message(client):
    assert client.get("/api/v1/next?track=practical").json() == {
        "pick": None,
        "message": "nothing due and no new problems in scope",
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
    }


def test_the_problem_document_carries_the_jdk_range_of_the_listing(client, environment):
    document = client.get("/api/v1/problems/two-sum").json()
    assert document["jdk"] == {"min": 21, "max": 26}
