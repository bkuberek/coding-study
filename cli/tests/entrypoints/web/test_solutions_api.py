"""Reference solutions in the page, behind the confirmation `cstudy solution` asks
(docs/specs/web-ui.md#solutions)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import Attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.markdown import render_markdown
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.web_server import WRITE_HEADERS, session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
SOLUTION = "/api/v1/problems/two-sum/solution"
REVEAL_QUESTION = "Reveal the solution? The attempt will be graded as again."
HASH_MAP_LINE = "seen: dict[int, int] = {}"
BRUTE_FORCE_LINE = "for j in range(i + 1, len(nums)):"


@pytest.fixture
def practice(tmp_path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    return make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))


@pytest.fixture
def unsolved(practice) -> Attempt:
    return start_attempt(practice, StartRequest("two-sum", Language.PYTHON)).attempt


def post(tmp_path: Path, environment: Environment, body: object, path: str = SOLUTION):
    with session_client(web_app(tmp_path, environment)) as client:
        return client.post(path, json=body, headers=WRITE_HEADERS)


def error(response) -> tuple[int, str, str]:
    found = response.json()["error"]
    return response.status_code, found["code"], found["message"]


def revealed(environment: Environment, attempt: Attempt) -> bool:
    current = environment.progress.attempt(attempt.id)
    assert current is not None
    return current.solution_revealed


def test_without_an_attempt_the_solution_shows_at_once(tmp_path, practice):
    document = post(tmp_path, practice, {}).json()
    assert (document["slug"], document["kind"], document["language"], document["approaches"]) == (
        "two-sum",
        "function",
        "python",
        ["hash-map"],
    )


def test_the_default_approach_shows_its_code(tmp_path, practice):
    assert HASH_MAP_LINE in post(tmp_path, practice, {}).json()["markdown"]


def test_the_html_is_the_markdown_rendered(tmp_path, practice):
    document = post(tmp_path, practice, {}).json()
    assert document["html"] == render_markdown(document["markdown"])


def test_without_an_attempt_nothing_is_marked(tmp_path, practice):
    assert post(tmp_path, practice, {}).json()["marked_attempt_id"] is None


def test_an_unsolved_attempt_needs_a_confirmation(tmp_path, practice, unsolved):
    response = post(tmp_path, practice, {})
    assert error(response) == (409, "confirmation_required", REVEAL_QUESTION)


def test_asking_marks_nothing(tmp_path, practice, unsolved):
    post(tmp_path, practice, {})
    assert not revealed(practice, unsolved)


def test_a_confirmed_reveal_marks_the_attempt(tmp_path, practice, unsolved):
    document = post(tmp_path, practice, {"confirm": True}).json()
    assert (document["marked_attempt_id"], revealed(practice, unsolved)) == (unsolved.id, True)


def test_a_passed_attempt_shows_without_a_confirmation(tmp_path, practice, unsolved):
    practice.progress.update_attempt(replace(unsolved, first_pass_at=NOW))
    response = post(tmp_path, practice, {})
    assert (response.status_code, response.json()["marked_attempt_id"]) == (200, None)


def test_a_solution_during_a_mock_gets_the_lock_message(tmp_path, practice):
    request = StartRequest("lru-cache", Language.PYTHON, fresh=True, timer_s=45 * 60, mock=True)
    start_attempt(practice, request)
    assert error(post(tmp_path, practice, {"confirm": True})) == (
        422,
        "usage",
        "cstudy solution is locked during the mock interview (lru-cache; 45:00 left); it "
        "unlocks when the timer ends or every problem is done",
    )


def test_an_approach_shows_that_approach(tmp_path, practice):
    document = post(tmp_path, practice, {"approach": "brute-force"}).json()
    assert (document["approaches"], BRUTE_FORCE_LINE in document["markdown"]) == (
        ["brute-force"],
        True,
    )


def test_all_shows_every_approach_in_ladder_order(tmp_path, practice):
    assert post(tmp_path, practice, {"all": True}).json()["approaches"] == [
        "brute-force",
        "hash-map",
    ]


def test_an_unknown_approach_gets_the_clis_refusal(tmp_path, practice):
    assert error(post(tmp_path, practice, {"approach": "sorting"})) == (
        422,
        "usage",
        'no approach "sorting" in two-sum; approaches: brute-force, hash-map',
    )


def test_a_language_without_a_reference_says_which_have_one(tmp_path, practice):
    markdown = post(tmp_path, practice, {"language": "kotlin"}).json()["markdown"]
    assert "no kotlin reference; available: python" in markdown


def test_explanation_only_shows_no_code(tmp_path, practice):
    markdown = post(tmp_path, practice, {"explanation_only": True}).json()["markdown"]
    assert (HASH_MAP_LINE in markdown, "## Approach: hash-map" in markdown) == (False, True)


def test_broken_on_a_problem_without_broken_references_gets_422(tmp_path, practice):
    assert error(post(tmp_path, practice, {"broken": True})) == (
        422,
        "usage",
        "two-sum has no broken references (concurrent problems and projects with stress "
        "cases only)",
    )


def test_code_holding_a_fence_gets_a_longer_fence(tmp_path, practice):
    reference = practice.root / "problems" / "0001-two-sum" / "solutions" / "hash-map.py"
    reference.write_text(reference.read_text() + '\nFENCE = """```"""\n')
    assert "````python" in post(tmp_path, practice, {}).json()["markdown"]


def test_an_unknown_problem_gets_404(tmp_path, practice):
    response = post(tmp_path, practice, {}, "/api/v1/problems/no-such/solution")
    assert error(response)[:2] == (404, "not_found")


def test_a_projects_changed_file_shows_as_a_diff(tmp_path):
    project = project_environment(tmp_path, ScriptedProjectProcess())
    path = f"/api/v1/problems/{PROJECT_SLUG}/solution"
    markdown = post(tmp_path, project, {}, path).json()["markdown"]
    assert "**bank/bank.py** (changed)\n\n```diff" in markdown


# items


ITEM = "/api/v1/problems/url-shortener/solution"


def test_an_items_rubric_and_reference_show_without_a_confirmation(tmp_path, practice):
    start_item_attempt(practice, ItemStartRequest("url-shortener"))
    document = post(tmp_path, practice, {}, ITEM).json()
    assert (document["kind"], document["language"], document["marked_attempt_id"]) == (
        "item",
        None,
        None,
    )
    assert "Pre-generated random keys" in document["markdown"]


def test_an_items_reveal_is_recorded(tmp_path, practice):
    attempt = start_item_attempt(practice, ItemStartRequest("url-shortener")).attempt
    post(tmp_path, practice, {}, ITEM)
    assert revealed(practice, attempt)


def test_an_item_with_a_language_gets_the_clis_refusal(tmp_path, practice):
    assert error(post(tmp_path, practice, {"language": "python"}, ITEM)) == (
        422,
        "usage",
        "url-shortener is not autograded; "
        "--lang, --approach, --all and --explanation-only apply to problems",
    )
