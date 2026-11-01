"""Mock interviews from the page: `POST /api/v1/mock` starts one as `cstudy mock` does, and
`GET /api/v1/mock` shows the one that runs, wherever it started
(docs/specs/web-ui.md#mock-progress-and-health). The catalog slice is that of `cstudy mock`'s
tests: two easy problems, lru-cache and group-anagrams (medium), first-missing-positive (hard)
and the fixture items."""

from dataclasses import replace
from datetime import timedelta

import pytest

from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.environment import Environment
from coding_study.application.mock_interview import MockRequest, start_mock
from coding_study.application.ports import StubGenerator
from coding_study.domain.problem import Language
from tests.fakes import (
    NOW,
    FakeStubGenerator,
    FakeToolchains,
    jdk_of,
    make_environment,
    repository_root,
)
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, copy_catalog_problems
from tests.web_server import WRITE_HEADERS, session_client, web_app

SLICE = (*FIRST_CATALOG, "0007-group-anagrams", "0014-first-missing-positive")
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
MOCK = "/api/v1/mock"
ENDS_AT = (NOW + timedelta(minutes=45)).isoformat()


@pytest.fixture(scope="module")
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), SLICE)


@pytest.fixture
def environment(tmp_path, problems) -> Environment:
    root = repository_root(tmp_path, problems, FIXTURE_TRACKS)
    return make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))


def post(tmp_path, environment: Environment, body: object):
    with session_client(web_app(tmp_path, environment)) as client:
        return client.post(MOCK, json=body, headers=WRITE_HEADERS)


def get(tmp_path, environment: Environment):
    with session_client(web_app(tmp_path, environment)) as client:
        return client.get(MOCK)


def in_progress(environment: Environment) -> dict[str, int]:
    return {attempt.slug: attempt.id for attempt in environment.progress.attempts_in_progress()}


# POST


def test_a_mock_answers_201_with_its_problems(tmp_path, environment):
    response = post(tmp_path, environment, {})
    slugs = [problem["slug"] for problem in response.json()["problems"]]
    assert (response.status_code, slugs) == (201, ["group-anagrams", "lru-cache"])


def test_a_mock_names_each_problems_attempt(tmp_path, environment):
    problems = post(tmp_path, environment, {}).json()["problems"]
    assert {problem["slug"]: problem["attempt_id"] for problem in problems} == in_progress(
        environment
    )


def test_a_mock_answers_its_settings_and_shared_end(tmp_path, environment):
    document = post(tmp_path, environment, {}).json()
    assert {key: document[key] for key in ("minutes", "count", "language", "ends_at")} == {
        "minutes": 45,
        "count": 2,
        "language": "python",
        "ends_at": ENDS_AT,
    }


def test_a_mock_problem_is_described_as_cstudy_mock_lists_it(tmp_path, environment):
    problem = post(tmp_path, environment, {}).json()["problems"][1]
    assert {key: value for key, value in problem.items() if key != "attempt_id"} == {
        "slug": "lru-cache",
        "title": "LRU Cache",
        "difficulty": "medium",
        "group": "linked-list",
        "reason": "weakest pattern: linked-list (0.75)",
        "kind": "design",
        "file": "python/practice/lru_cache.py",
        "statement": ".statements/lru-cache.md",
    }


def test_minutes_and_count_set_the_mock(tmp_path, environment):
    post(tmp_path, environment, {"minutes": 30, "count": 1})
    attempts = environment.progress.attempts_in_progress()
    assert [(attempt.slug, attempt.time_limit_s) for attempt in attempts] == [
        ("group-anagrams", 1800)
    ]


def test_tracks_and_language_choose_the_scope(tmp_path, environment):
    body = {"tracks": ["system-design"], "count": 1, "language": "kotlin"}
    problem = post(tmp_path, environment, body).json()["problems"][0]
    assert (problem["slug"], problem["kind"], problem["file"]) == (
        "url-shortener",
        "item",
        "notes/system-design/url-shortener.md",
    )


def test_nothing_in_scope_answers_200_with_the_clis_message(tmp_path, environment):
    response = post(tmp_path, environment, {"tracks": ["practical"]})
    document = response.json()
    assert (response.status_code, document["problems"], document["message"]) == (
        200,
        [],
        "no new medium or hard problems in scope",
    )


def test_a_jdk_that_took_out_every_problem_is_named_in_the_message(tmp_path, environment):
    selecting = replace(environment, jdk=jdk_of(27))
    document = post(tmp_path, selecting, {"language": "java"}).json()
    assert (document["problems"], document["message"]) == (
        [],
        "no new medium or hard problems in scope: "
        "JDK 27 (JAVA_HOME) cannot run java problems; cstudy supports JDK 21 to 26",
    )


def test_a_mock_while_one_runs_gets_the_lock_message(tmp_path, environment):
    post(tmp_path, environment, {})
    response = post(tmp_path, environment, {})
    assert (response.status_code, response.json()["error"]["message"]) == (
        422,
        "cstudy mock is locked during the mock interview (group-anagrams, lru-cache; 45:00 "
        "left); it unlocks when the timer ends or every problem is done",
    )


@pytest.mark.parametrize(
    "body",
    [{"minutes": 0}, {"minutes": 601}, {"count": 0}, {"tracks": "dsa"}, {"tracks": ["chess"]}],
)
def test_a_value_cstudy_mock_refuses_gets_422(tmp_path, environment, body):
    assert post(tmp_path, environment, body).status_code == 422


# GET


def test_no_mock_answers_not_running(tmp_path, environment):
    assert get(tmp_path, environment).json() == {"running": False}


def test_a_mock_started_in_the_terminal_shows(tmp_path, environment):
    start_mock(environment, MockRequest())
    ids = in_progress(environment)
    assert get(tmp_path, environment).json() == {
        "running": True,
        "ends_at": ENDS_AT,
        "remaining_s": 2700,
        "attempts": [
            {
                "attempt_id": ids["group-anagrams"],
                "slug": "group-anagrams",
                "title": "Group Anagrams",
                "difficulty": "medium",
                "kind": "function",
                "language": "python",
            },
            {
                "attempt_id": ids["lru-cache"],
                "slug": "lru-cache",
                "title": "LRU Cache",
                "difficulty": "medium",
                "kind": "design",
                "language": "python",
            },
        ],
        "locked": ["hint", "solution", "mock"],
    }


def test_the_remaining_time_counts_down(tmp_path, environment):
    start_mock(environment, MockRequest())
    environment.clock.advance(timedelta(minutes=13, seconds=40))  # type: ignore[attr-defined]
    assert get(tmp_path, environment).json()["remaining_s"] == 1880


def test_a_finished_problem_leaves_the_mock(tmp_path, environment):
    start_mock(environment, MockRequest())
    complete_attempt(environment, DoneRequest("group-anagrams", gave_up=True))
    attempts = get(tmp_path, environment).json()["attempts"]
    assert [attempt["slug"] for attempt in attempts] == ["lru-cache"]


def test_the_mock_ends_with_its_timer(tmp_path, environment):
    start_mock(environment, MockRequest())
    environment.clock.advance(timedelta(minutes=45))  # type: ignore[attr-defined]
    assert get(tmp_path, environment).json() == {"running": False}
