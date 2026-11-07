"""`/api/v1/sets`, and `set` on `GET /api/v1/problems` and `GET /api/v1/next`
(docs/specs/web-ui.md#sets): the documents of `cstudy set`, its refusals, and a file that does not
parse refused and kept."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems, next_problem, problem_sets
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.web_server import WRITE_HEADERS, session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
SETS = "/api/v1/sets"
LOOP = "backend-loop"
HAND_WRITTEN = f"""\
# Mine.
sets:
  # On the 12th.
  {LOOP}:
    description: The loop
    problems:
      - two-sum  # warm up
      - url-shortener
"""
runner = CliRunner()


@pytest.fixture
def environment(tmp_path: Path):
    return make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))


@pytest.fixture
def file(tmp_path: Path) -> Path:
    written = tmp_path / "sets.yaml"
    written.write_text(HAND_WRITTEN)
    return written


@pytest.fixture
def client(tmp_path: Path, environment):
    with session_client(web_app(tmp_path, environment)) as opened:
        yield opened


def post(client, path: str, **body: object):
    return client.post(f"{SETS}{path}", json=body, headers=WRITE_HEADERS)


def delete(client, path: str, **body: object):
    return client.request("DELETE", f"{SETS}{path}", json=body, headers=WRITE_HEADERS)


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def finish(environment, slug: str) -> None:
    progress = environment.progress
    attempt = progress.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.NEW, NOW))
    progress.update_attempt(
        replace(attempt, status=AttemptStatus.PASSED, ended_at=NOW, grade=Grade.OK)
    )


def cli_document(monkeypatch, environment, *arguments: str):
    for module in (problem_sets, list_problems, next_problem):
        monkeypatch.setattr(module, "load_environment", lambda *_: environment)
    return json.loads(runner.invoke(cli.app, [*arguments, "--json"]).stdout)


def test_no_file_answers_no_sets(client):
    assert client.get(SETS).json() == {"sets": []}


def test_the_list_is_the_document_of_cstudy_set_list(client, file, environment, monkeypatch):
    finish(environment, "two-sum")
    assert client.get(SETS).json() == cli_document(monkeypatch, environment, "set", "list")


def test_a_set_is_the_document_of_cstudy_set_show(client, file, environment, monkeypatch):
    finish(environment, "two-sum")
    expected = cli_document(monkeypatch, environment, "set", "show", LOOP)
    assert client.get(f"{SETS}/{LOOP}").json() == expected


def test_an_unknown_set_gets_404_naming_your_sets(client, file):
    response = client.get(f"{SETS}/nope")
    assert (error(response), LOOP in response.json()["error"]["message"]) == (
        (404, "not_found"),
        True,
    )


def test_creating_answers_201_with_the_new_set(client, file):
    response = post(client, "", name="data-loop", description="Later")
    assert (response.status_code, response.json()["name"], response.json()["description"]) == (
        201,
        "data-loop",
        "Later",
    )


def test_creating_keeps_the_file_as_written(client, file):
    post(client, "", name="data-loop")
    assert file.read_text().startswith(HAND_WRITTEN)


def test_creating_a_name_that_exists_gets_422_and_changes_nothing(client, file):
    response = post(client, "", name=LOOP)
    assert (error(response), file.read_text()) == ((422, "usage"), HAND_WRITTEN)


def test_a_name_that_is_not_a_slug_gets_the_cli_s_refusal(client):
    response = post(client, "", name="Backend Loop")
    assert (error(response), "such as backend-loop" in response.json()["error"]["message"]) == (
        (422, "usage"),
        True,
    )


def test_creating_needs_a_name(client):
    assert post(client, "").json()["error"]["message"] == "the request needs name"


def test_adding_says_what_it_added_and_answers_the_set(client, file):
    response = post(client, f"/{LOOP}/add", slugs=["lru-cache", "two-sum"])
    found = response.json()
    assert (found["added"], found["already"], [row["slug"] for row in found["set"]["rows"]]) == (
        ["lru-cache"],
        ["two-sum"],
        ["two-sum", "url-shortener", "lru-cache"],
    )


def test_adding_a_slug_in_no_catalog_gets_the_suggestion_and_adds_nothing(client, file):
    response = post(client, f"/{LOOP}/add", slugs=["lru-cache", "two-summ"])
    assert (error(response), file.read_text(), "did you mean two-sum?") == (
        (422, "usage"),
        HAND_WRITTEN,
        response.json()["error"]["message"].split("; ")[-1],
    )


def test_adding_needs_a_list_of_slugs(client, file):
    assert error(post(client, f"/{LOOP}/add", slugs="two-sum")) == (422, "usage")


def test_adding_needs_slugs(client, file):
    assert post(client, f"/{LOOP}/add").json()["error"]["message"] == "the request needs slugs"


def test_a_list_of_anything_but_text_is_refused(client, file):
    assert error(post(client, f"/{LOOP}/add", slugs=[1])) == (422, "usage")


def test_removing_says_what_it_removed(client, file):
    found = post(client, f"/{LOOP}/remove", slugs=["two-sum", "lru-cache"]).json()
    assert (found["removed"], found["absent"], [row["slug"] for row in found["set"]["rows"]]) == (
        ["two-sum"],
        ["lru-cache"],
        ["url-shortener"],
    )


def test_moving_answers_the_set_in_its_new_order(client, file):
    found = post(client, f"/{LOOP}/move", slug="url-shortener", position=1).json()
    assert [row["slug"] for row in found["rows"]] == ["url-shortener", "two-sum"]


def test_moving_keeps_the_comments(client, file):
    post(client, f"/{LOOP}/move", slug="url-shortener", position=1)
    assert "- two-sum  # warm up" in file.read_text()


def test_moving_outside_the_list_gets_422(client, file):
    assert error(post(client, f"/{LOOP}/move", slug="two-sum", position=9)) == (422, "usage")


def test_moving_needs_a_position(client, file):
    response = post(client, f"/{LOOP}/move", slug="two-sum")
    assert response.json()["error"]["message"] == "the request needs position"


@pytest.mark.parametrize("position", ["1", True, 1.5])
def test_a_position_of_another_type_is_refused(client, file, position):
    assert error(post(client, f"/{LOOP}/move", slug="two-sum", position=position)) == (
        422,
        "usage",
    )


def test_renaming_answers_the_renamed_set(client, file):
    found = post(client, f"/{LOOP}/rename", to="platform-loop").json()
    assert (found["name"], len(found["rows"])) == ("platform-loop", 2)


def test_renaming_to_a_name_that_exists_gets_422(client, file):
    post(client, "", name="data-loop")
    assert error(post(client, f"/{LOOP}/rename", to="data-loop")) == (422, "usage")


def test_deleting_without_confirm_asks_and_changes_nothing(client, file):
    response = delete(client, f"/{LOOP}")
    assert (error(response), file.read_text()) == ((409, "confirmation_required"), HAND_WRITTEN)


def test_the_question_says_progress_stays(client, file):
    assert "progress stays" in delete(client, f"/{LOOP}").json()["error"]["message"]


def test_deleting_with_confirm_takes_the_set_out(client, file):
    response = delete(client, f"/{LOOP}", confirm=True)
    assert (response.json(), client.get(SETS).json()) == ({"deleted": LOOP}, {"sets": []})


def test_deleting_an_unknown_set_gets_404(client, file):
    assert error(delete(client, "/nope", confirm=True)) == (404, "not_found")


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "", None),
        ("GET", f"/{LOOP}", None),
        ("POST", "", {"name": "other"}),
        ("POST", f"/{LOOP}/add", {"slugs": ["two-sum"]}),
        ("POST", f"/{LOOP}/remove", {"slugs": ["two-sum"]}),
        ("POST", f"/{LOOP}/move", {"slug": "two-sum", "position": 1}),
        ("POST", f"/{LOOP}/rename", {"to": "other"}),
        ("DELETE", f"/{LOOP}", {"confirm": True}),
    ],
)
def test_a_file_that_does_not_parse_gets_503_and_is_kept(client, file, method, path, body):
    broken = "sets: [unclosed\n"
    file.write_text(broken)
    headers = WRITE_HEADERS if body is not None else {}
    response = client.request(method, f"{SETS}{path}", json=body, headers=headers)
    assert (error(response), file.read_text(), response.json()["error"]["message"][:9]) == (
        (503, "environment"),
        broken,
        "sets.yaml",
    )


def test_the_problems_of_a_set_are_the_document_of_cstudy_list_set(
    client, file, environment, monkeypatch
):
    expected = cli_document(monkeypatch, environment, "list", "--set", LOOP)
    assert client.get("/api/v1/problems", params={"set": LOOP}).json() == expected


def test_the_problems_of_a_set_keep_its_order(client, file):
    post(client, f"/{LOOP}/move", slug="url-shortener", position=1)
    entries = client.get("/api/v1/problems", params={"set": LOOP}).json()["entries"]
    assert [entry["slug"] for entry in entries] == ["url-shortener", "two-sum"]


def test_the_problems_combine_the_set_with_the_other_filters(client, file):
    entries = client.get("/api/v1/problems", params={"set": LOOP, "kind": "item"}).json()["entries"]
    assert [entry["slug"] for entry in entries] == ["url-shortener"]


def test_the_problems_of_an_unknown_set_get_404(client, file):
    assert error(client.get("/api/v1/problems", params={"set": "nope"})) == (404, "not_found")


def test_the_pick_of_a_set_is_the_document_of_cstudy_next_set(
    client, file, environment, monkeypatch
):
    expected = cli_document(monkeypatch, environment, "next", "--set", LOOP)
    assert client.get("/api/v1/next", params={"set": LOOP}).json() == expected


def test_the_pick_says_when_a_set_is_finished(client, file, environment):
    finish(environment, "two-sum")
    finish(environment, "url-shortener")
    assert client.get("/api/v1/next", params={"set": LOOP}).json()["message"] == (
        f"{LOOP} is finished: 2 of 2 passed"
    )


def test_a_file_that_does_not_parse_leaves_the_plain_list_and_pick(client, file):
    file.write_text("sets: [unclosed\n")
    codes = [client.get("/api/v1/problems").status_code, client.get("/api/v1/next").status_code]
    assert codes == [200, 200]
