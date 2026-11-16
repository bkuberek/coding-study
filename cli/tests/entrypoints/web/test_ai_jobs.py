"""The AI jobs and the stored reviews over HTTP (docs/specs/web-ui.md#jobs and #ai-preview): the
pre-checks that keep a job from starting only to fail, the consent 409 and `confirm`, the reviews
list and dismiss, and a real child `cstudy` that reaches the fake provider while the server
process sends nothing. A key is in no response."""

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from starlette.testclient import TestClient
from typer.testing import CliRunner

from coding_study.adapters.ai.http_json import ENDPOINT_VARIABLE
from coding_study.adapters.environment_factory import load_environment
from coding_study.application.ai_review import list_reviews, plan_review, show_review
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.ai import AI_OFF, AiTask, ApiKey, ModelRef, Provider, Routing
from coding_study.domain.ai_records import Consent, ReviewItem, ReviewRecord, Verdict
from coding_study.domain.config import AiSettings, Config
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands.ai_review_report import list_document, review_document
from coding_study.entrypoints.web.children import ChildCommand
from coding_study.entrypoints.web.runs import Children
from tests.fake_ai_provider import Answer, FakeAiProvider, Route
from tests.fakes import (
    NOW,
    FakeClock,
    FakeCredentials,
    ScriptedLanguageModels,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS, SCHEMAS_DIRECTORY
from tests.scripted_runs import QUICK, Script, eventually, frames, lines_of
from tests.web_server import WRITE_HEADERS, session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
JOBS = "/api/v1/jobs"
SLUG = "url-shortener"
NOTES = "notes/system-design/url-shortener.md"
ANSWER = "## Requirements\n\nRedirects stay fast even when creating links is down.\n"
SECRET = "sk-sentinel-0123456789"
ANTHROPIC = ModelRef(Provider.ANTHROPIC, "claude-x")
OPENROUTER = ModelRef(Provider.OPENROUTER, "vendor/model")
FIXED = AiSettings(enabled=True, model=ANTHROPIC)
AUTO = AiSettings(enabled=True, routing=Routing.AUTO, fast=OPENROUTER, strong=ANTHROPIC)
KEYS = {Provider.ANTHROPIC: SECRET, Provider.OPENROUTER: SECRET}
CHECKED_BY_TESTS = "two-sum"
REVIEW = {"command": "ai_review", "slug": SLUG}
CHECK = {"command": "ai_check"}
MODELS = {"command": "ai_models", "provider": "anthropic"}
TERMS = "Your anthropic account's terms apply to what it receives."


class Served:
    """A workspace with url-shortener started and its notes written, a server over it whose
    children are scripted, and the models the server itself would send with, which no test lets
    answer."""

    def __init__(self, tmp_path: Path, settings: AiSettings, keys, notes: str | None) -> None:
        self.root = repository_root(tmp_path / "workspace", PRACTICE, FIXTURE_RUBRIC_PROBLEMS)
        self.models = ScriptedLanguageModels()
        self.environment = make_environment(
            self.root,
            config=Config(ai=settings),
            credentials=FakeCredentials(keys),
            models=self.models,
            clock=FakeClock(),
        )
        start_item_attempt(self.environment, ItemStartRequest(SLUG))
        if notes is None:
            self.environment.workspace.absolute(NOTES).unlink()
        else:
            self.environment.workspace.write_text(NOTES, notes)
        self.script = Script(tmp_path / "script.json")
        self.script.play({"out": "reviewing"}, {"exit": 0})
        self.children = Children(QUICK)
        self.app = web_app(tmp_path / "server", self.environment, self.script.child, self.children)

    def consented(self, model: ModelRef, task: AiTask) -> None:
        self.environment.ai_store.grant_consent(Consent(model.provider, model.model_id, task, NOW))

    def consents(self) -> list[tuple[str, str, str]]:
        return [
            (consent.provider.value, consent.model, consent.purpose.value)
            for consent in self.environment.ai_store.consents()
        ]


@pytest.fixture
def serve(tmp_path):
    def make(settings: AiSettings = FIXED, keys=KEYS, notes: str | None = ANSWER) -> Served:
        (tmp_path / "server").mkdir(exist_ok=True)
        return Served(tmp_path, settings, keys, notes)

    return make


def start(client: TestClient, body: Mapping[str, object]):
    return client.post(JOBS, json=body, headers=WRITE_HEADERS)


def ran(client: TestClient, served: Served, response) -> list[str]:
    """The `cstudy` arguments of the job a 201 started, once it ended."""
    assert response.status_code == 201, response.text
    client.get(f"{JOBS}/{response.json()['id']}/events")
    return served.script.arguments()


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def nothing_started(served: Served, *responses) -> bool:
    """No child ran, no consent was recorded and nothing left the server, and no response holds
    the key."""
    shown = "".join(f"{response.headers}{response.text}" for response in responses)
    return (
        served.script.calls() == []
        and served.consents() == []
        and served.models.requests == []
        and SECRET not in shown
    )


def consent_validator() -> Draft202012Validator:
    schema = json.loads((SCHEMAS_DIRECTORY / "web-api.schema.json").read_text())
    return Draft202012Validator({"$ref": "#/$defs/ai_consent", "$defs": schema["$defs"]})


# ai_review: the consent 409


def test_a_review_without_consent_gets_the_consent_document(serve):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, REVIEW)
    body = response.json()["error"]
    assert error(response) == (409, "confirmation_required")
    assert body["message"] == (
        f"AI review of {SLUG} sends your notes to anthropic:claude-x. Send it?"
    )
    consent = body["consent"]
    assert [item["label"] for item in consent["sends"]] == [
        "instructions review-1",
        "prompt.md",
        "rubric.md, 5 criteria",
        f"your notes, {NOTES}",
    ]
    assert all(item["bytes"] > 0 for item in consent["sends"])
    assert {key: value for key, value in consent.items() if key != "sends"} == {
        "purpose": "review",
        "models": [{"tier": None, "provider": "anthropic", "model": "claude-x"}],
        "input_tokens": consent["input_tokens"],
        "output_tokens": 16_000,
        "today": {"tokens": 0, "cap": FIXED.daily_token_cap},
        "terms": TERMS,
    }
    assert consent["input_tokens"] > 0
    assert list(consent_validator().iter_errors(consent)) == []
    assert nothing_started(served, response)


def test_the_size_of_the_notes_in_the_document_is_the_size_on_disk(serve):
    served = serve()
    with session_client(served.app) as client:
        consent = start(client, REVIEW).json()["error"]["consent"]
    notes = next(item for item in consent["sends"] if item["label"].startswith("your notes"))
    assert notes["bytes"] == len(ANSWER.encode())


def test_a_confirmed_review_records_the_consent_and_starts_the_child(serve):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, {**REVIEW, "confirm": True})
        job = response.json()["id"]
        text = client.get(f"{JOBS}/{job}/events").text
        arguments = served.script.arguments()
    assert response.status_code == 201
    assert served.consents() == [("anthropic", "claude-x", "review")]
    assert arguments == ["ai", "review", "--", SLUG]
    assert [frame.data["exit_code"] for frame in frames(text) if frame.event == "closed"] == [0]
    assert served.models.requests == []


def test_a_review_with_consent_starts_without_a_question(serve):
    served = serve()
    served.consented(ANTHROPIC, AiTask.REVIEW)
    with session_client(served.app) as client:
        arguments = ran(client, served, start(client, REVIEW))
    assert arguments == ["ai", "review", "--", SLUG]
    assert served.consents() == [("anthropic", "claude-x", "review")]


def test_a_consent_for_another_model_or_purpose_does_not_count(serve):
    served = serve()
    served.consented(ANTHROPIC, AiTask.CHECK)
    served.consented(ModelRef(Provider.ANTHROPIC, "claude-y"), AiTask.REVIEW)
    with session_client(served.app) as client:
        response = start(client, REVIEW)
    assert error(response) == (409, "confirmation_required")
    assert served.script.calls() == []


def test_confirm_on_a_review_that_needs_none_changes_nothing_more(serve):
    served = serve()
    served.consented(ANTHROPIC, AiTask.REVIEW)
    with session_client(served.app) as client:
        response = start(client, {**REVIEW, "confirm": True})
    assert response.status_code == 201
    assert len(served.consents()) == 1


def test_confirm_does_not_skip_a_refusal(serve):
    served = serve(keys={})
    with session_client(served.app) as client:
        response = start(client, {**REVIEW, "confirm": True})
    assert error(response) == (422, "usage")
    assert nothing_started(served, response)


# ai_review: refusals


TEMPLATE = "# Notes\n\n<!-- write here -->\n"


@pytest.mark.parametrize(
    ("settings", "keys", "notes", "words"),
    [
        (AiSettings(), KEYS, ANSWER, AI_OFF),
        (AiSettings(enabled=True), KEYS, ANSWER, "ai.model is not set"),
        (FIXED, {}, ANSWER, "no key for anthropic"),
        (FIXED, KEYS, TEMPLATE, "still the template"),
        (FIXED, KEYS, None, "is missing"),
        (replace(FIXED, daily_token_cap=100), KEYS, ANSWER, "cap"),
    ],
)
def test_a_review_that_the_command_would_refuse_is_422_with_its_message(
    serve, settings, keys, notes, words
):
    served = serve(settings, keys, notes)
    with session_client(served.app) as client:
        response = start(client, REVIEW)
    assert error(response) == (422, "usage")
    assert words in response.json()["error"]["message"]
    assert nothing_started(served, response)


def test_a_review_of_a_problem_checked_by_tests_is_422(serve):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, {"command": "ai_review", "slug": CHECKED_BY_TESTS})
    assert error(response) == (422, "usage")
    assert "AI review is for rubric problems" in response.json()["error"]["message"]
    assert nothing_started(served, response)


def test_a_review_without_an_attempt_is_422(serve):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, {"command": "ai_review", "slug": "news-feed"})
    assert error(response) == (422, "usage")
    assert "no attempt of news-feed yet" in response.json()["error"]["message"]
    assert nothing_started(served, response)


def test_a_review_of_an_unknown_problem_is_404(serve):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, {"command": "ai_review", "slug": "no-such-problem"})
    assert error(response) == (404, "not_found")
    assert nothing_started(served, response)


@pytest.mark.parametrize(
    "body",
    [
        {"command": "ai_review"},
        {"command": "ai_review", "slug": ""},
        {"command": "ai_review", "slug": 5},
        {"command": "ai_review", "slug": SLUG, "confirm": "yes"},
        {"command": "ai_review", "slug": SLUG, "provider": "anthropic"},
        {"command": "ai_review", "slug": SLUG, "model": "anthropic:claude-x"},
    ],
)
def test_a_review_with_options_it_does_not_take_is_422(serve, body):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, body)
    assert error(response) == (422, "usage")
    assert nothing_started(served, response)


def test_a_slug_that_looks_like_an_option_stays_an_argument(serve):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, {"command": "ai_review", "slug": "--dry-run"})
    assert error(response) == (404, "not_found")
    assert served.script.calls() == []


# ai_check


def test_the_check_without_consent_lists_each_model_that_lacks_it(serve):
    served = serve(AUTO)
    served.consented(OPENROUTER, AiTask.CHECK)
    with session_client(served.app) as client:
        first = start(client, CHECK)
        served.consented(OPENROUTER, AiTask.REVIEW)
        served.environment.ai_store.revoke_consent(
            Provider.OPENROUTER, "vendor/model", AiTask.CHECK
        )
        both = start(client, CHECK)
    assert error(first) == (409, "confirmation_required")
    assert first.json()["error"]["consent"]["models"] == [
        {"tier": "strong", "provider": "anthropic", "model": "claude-x"}
    ]
    consent = both.json()["error"]["consent"]
    assert [(model["tier"], model["model"]) for model in consent["models"]] == [
        ("fast", "vendor/model"),
        ("strong", "claude-x"),
    ]
    assert both.json()["error"]["message"] == (
        "The check sends a fixed test message to openrouter:vendor/model and anthropic:claude-x. "
        "Send it?"
    )
    assert consent["terms"] == (
        "Your openrouter account's terms apply to what it receives. " + TERMS
    )
    assert list(consent_validator().iter_errors(consent)) == []
    assert served.script.calls() == []


def test_the_check_document_lists_what_it_sends(serve):
    served = serve()
    with session_client(served.app) as client:
        consent = start(client, CHECK).json()["error"]["consent"]
    assert [(item["label"], item["bytes"] is None) for item in consent["sends"]] == [
        ("instructions check-1", False),
        ("a fixed test message", False),
        ("nothing of yours", True),
    ]
    assert (consent["purpose"], consent["output_tokens"]) == ("check", 1_000)


def test_a_confirmed_check_records_a_consent_for_each_model_and_starts_the_child(serve):
    served = serve(AUTO)
    with session_client(served.app) as client:
        arguments = ran(client, served, start(client, {**CHECK, "confirm": True}))
    assert sorted(served.consents()) == [
        ("anthropic", "claude-x", "check"),
        ("openrouter", "vendor/model", "check"),
    ]
    assert arguments == ["ai", "check"]
    assert served.models.requests == []


def test_a_check_with_every_consent_starts_without_a_question(serve):
    served = serve(AUTO)
    served.consented(OPENROUTER, AiTask.CHECK)
    served.consented(ANTHROPIC, AiTask.CHECK)
    with session_client(served.app) as client:
        arguments = ran(client, served, start(client, CHECK))
    assert arguments == ["ai", "check"]


def test_a_review_consent_is_no_check_consent(serve):
    served = serve()
    served.consented(ANTHROPIC, AiTask.REVIEW)
    with session_client(served.app) as client:
        response = start(client, CHECK)
    assert error(response) == (409, "confirmation_required")


@pytest.mark.parametrize(
    ("settings", "keys", "words"),
    [
        (AiSettings(), KEYS, AI_OFF),
        (AiSettings(enabled=True), KEYS, "ai.model is not set"),
        (FIXED, {}, "no key for anthropic"),
        (replace(AUTO, fast=None), KEYS, "ai.fast"),
        (replace(FIXED, daily_token_cap=1), KEYS, "cap"),
    ],
)
def test_a_check_that_the_command_would_refuse_is_422_with_its_message(
    serve, settings, keys, words
):
    served = serve(settings, keys)
    with session_client(served.app) as client:
        response = start(client, {**CHECK, "confirm": True})
    assert error(response) == (422, "usage")
    assert words in response.json()["error"]["message"]
    assert nothing_started(served, response)


@pytest.mark.parametrize("body", [{**CHECK, "provider": "anthropic"}, {**CHECK, "confirm": 1}])
def test_a_check_with_options_it_does_not_take_is_422(serve, body):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, body)
    assert error(response) == (422, "usage")
    assert nothing_started(served, response)


# ai_models


def test_models_start_with_a_key_and_ask_for_no_consent(serve):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, MODELS)
        arguments = ran(client, served, response)
        job = client.get(f"{JOBS}/{response.json()['id']}")
    assert arguments == ["ai", "models", "anthropic"]
    assert job.json()["command"] == "ai_models"
    assert job.json()["options"] == {"provider": "anthropic"}
    assert (served.consents(), served.models.listed, served.models.requests) == ([], [], [])
    assert SECRET not in job.text + response.text


def test_models_of_each_provider_are_the_child_of_that_provider(serve):
    served = serve()
    served.environment.credentials.save_key(Provider.GOOGLE, ApiKey(SECRET))
    with session_client(served.app) as client:
        response = start(client, {"command": "ai_models", "provider": "google"})
        arguments = ran(client, served, response)
    assert arguments == ["ai", "models", "google"]


@pytest.mark.parametrize(
    ("settings", "keys", "words"),
    [
        (AiSettings(), KEYS, AI_OFF),
        (FIXED, {}, "no key for anthropic: cstudy ai key anthropic, or Settings"),
    ],
)
def test_models_that_the_command_would_refuse_are_422_with_its_message(
    serve, settings, keys, words
):
    served = serve(settings, keys)
    with session_client(served.app) as client:
        response = start(client, MODELS)
    assert error(response) == (422, "usage")
    assert response.json()["error"]["message"] == words
    assert nothing_started(served, response)


@pytest.mark.parametrize(
    "body",
    [
        {"command": "ai_models"},
        {"command": "ai_models", "provider": ""},
        {"command": "ai_models", "provider": "nothing"},
        {"command": "ai_models", "provider": "--help"},
        {"command": "ai_models", "provider": 3},
        {"command": "ai_models", "provider": "anthropic", "confirm": True},
        {"command": "ai_models", "provider": "anthropic", "slug": SLUG},
    ],
)
def test_models_with_options_they_do_not_take_are_422(serve, body):
    served = serve()
    with session_client(served.app) as client:
        response = start(client, body)
    assert error(response) == (422, "usage")
    assert nothing_started(served, response)


# The slot and AI off


def test_an_ai_job_takes_the_one_job_slot(serve):
    served = serve()
    gate = served.script.gate("release")
    served.script.play({"out": "working"}, {"wait_for": str(gate)}, {"exit": 0})
    served.consented(ANTHROPIC, AiTask.REVIEW)
    with session_client(served.app) as client:
        first = start(client, REVIEW)
        second = start(client, MODELS)
        job = first.json()["id"]
        gate.write_text("go")
        eventually(lambda: client.get(f"{JOBS}/{job}").json()["state"], lambda s: s == "ended")
    assert (error(second), second.json()["error"]["job"]) == ((409, "conflict"), job)


def test_with_ai_off_every_ai_job_is_422_and_nothing_runs(serve):
    served = serve(AiSettings())
    with session_client(served.app) as client:
        responses = [
            start(client, {**REVIEW, "confirm": True}),
            start(client, {**CHECK, "confirm": True}),
            start(client, MODELS),
        ]
    assert [error(response) for response in responses] == [(422, "usage")] * 3
    assert nothing_started(served, *responses)


def test_the_lines_of_an_ai_job_stream_as_those_of_any_job(serve):
    served = serve()
    served.consented(ANTHROPIC, AiTask.REVIEW)
    with session_client(served.app) as client:
        job = start(client, REVIEW).json()["id"]
        text = client.get(f"{JOBS}/{job}/events").text
    assert [line["text"] for line in lines_of(frames(text), "line")] == ["reviewing"]


# The stored reviews


def stored_review(served: Served, **fields) -> int:
    attempt = served.environment.progress.active_attempt(SLUG)
    assert attempt is not None
    record = ReviewRecord(
        attempt_id=attempt.id,
        created_at=NOW,
        provider=Provider.ANTHROPIC,
        model="claude-x",
        prompt_version="review-1",
        rubric_sha256="0" * 64,
        notes_sha256="1" * 64,
        items=(ReviewItem(1, "Area", "Criterion", Verdict.PARTIAL, ("a quote",), "a gap"),),
        summary="A summary.",
        quotes_dropped=0,
        input_tokens=1_200,
        output_tokens=300,
        cost_usd=None,
    )
    return served.environment.ai_store.add_review(replace(record, **fields))


def schema_problems(name: str, document) -> list[str]:
    schema = json.loads((SCHEMAS_DIRECTORY / "cli" / f"{name}.schema.json").read_text())
    return [error.message for error in Draft202012Validator(schema).iter_errors(document)]


def reviews_of(slug: str) -> str:
    return f"/api/v1/problems/{slug}/ai-reviews"


def test_the_reviews_of_a_problem_are_the_document_of_the_command(serve):
    served = serve()
    first = stored_review(served)
    second = stored_review(served, summary="Another.")
    with session_client(served.app) as client:
        response = client.get(reviews_of(SLUG))
    document = response.json()
    assert (response.status_code, document) == (
        200,
        list_document(list_reviews(served.environment, SLUG)),
    )
    assert [review["review_id"] for review in document["reviews"]] == [second, first]
    assert schema_problems("ai-review-list", document) == []


def test_the_reviews_of_a_problem_with_none_are_an_empty_list(serve):
    served = serve()
    with session_client(served.app) as client:
        document = client.get(reviews_of(SLUG)).json()
    assert (document["slug"], document["reviews"]) == (SLUG, [])


def test_the_reviews_are_listed_with_ai_off(serve):
    served = serve(AiSettings())
    stored_review(served)
    with session_client(served.app) as client:
        response = client.get(reviews_of(SLUG))
    assert (response.status_code, len(response.json()["reviews"])) == (200, 1)


def test_the_reviews_of_a_problem_checked_by_tests_are_422(serve):
    served = serve()
    with session_client(served.app) as client:
        response = client.get(reviews_of(CHECKED_BY_TESTS))
    assert error(response) == (422, "usage")


def test_the_reviews_of_an_unknown_problem_are_404(serve):
    served = serve()
    with session_client(served.app) as client:
        response = client.get(reviews_of("no-such-problem"))
    assert error(response) == (404, "not_found")


def test_a_review_is_dismissed_and_stays_stored(serve):
    served = serve()
    review = stored_review(served)
    with session_client(served.app) as client:
        response = client.post(
            f"/api/v1/ai-reviews/{review}/dismiss", json={}, headers=WRITE_HEADERS
        )
        listing = client.get(reviews_of(SLUG)).json()
    document = response.json()
    assert response.status_code == 200
    assert document == review_document(show_review(served.environment, review))
    assert document["dismissed_at"] is not None
    assert [entry["dismissed_at"] for entry in listing["reviews"]] == [document["dismissed_at"]]
    assert schema_problems("ai-review", document) == []


def test_dismissing_a_review_again_changes_nothing(serve):
    served = serve()
    review = stored_review(served)
    path = f"/api/v1/ai-reviews/{review}/dismiss"
    with session_client(served.app) as client:
        first = client.post(path, json={}, headers=WRITE_HEADERS)
        served.environment.clock.current = NOW.replace(year=NOW.year + 1)
        again = client.post(path, json={}, headers=WRITE_HEADERS)
    assert (again.status_code, again.json()) == (200, first.json())


def test_dismissing_works_with_ai_off(serve):
    served = serve(AiSettings())
    review = stored_review(served)
    with session_client(served.app) as client:
        response = client.post(
            f"/api/v1/ai-reviews/{review}/dismiss", json={}, headers=WRITE_HEADERS
        )
    assert response.status_code == 200


@pytest.mark.parametrize("review", ["99", "0"])
def test_dismissing_an_unknown_review_is_404(serve, review):
    served = serve()
    with session_client(served.app) as client:
        response = client.post(
            f"/api/v1/ai-reviews/{review}/dismiss", json={}, headers=WRITE_HEADERS
        )
    assert error(response) == (404, "not_found")
    assert response.json()["error"]["message"] == f"no AI review {review}"


@pytest.mark.parametrize("review", ["x", "1.5", "-1"])
def test_dismissing_a_review_that_is_no_number_is_404(serve, review):
    served = serve()
    with session_client(served.app) as client:
        response = client.post(
            f"/api/v1/ai-reviews/{review}/dismiss", json={}, headers=WRITE_HEADERS
        )
    assert error(response) == (404, "not_found")


def test_dismissing_takes_an_object(serve):
    served = serve()
    review = stored_review(served)
    with session_client(served.app) as client:
        response = client.post(
            f"/api/v1/ai-reviews/{review}/dismiss", json=[], headers=WRITE_HEADERS
        )
    assert error(response) == (422, "usage")
    assert served.environment.ai_store.review(review).dismissed_at is None


# A real child


def review_reply(criteria: int) -> Answer:
    verdicts = [
        {"id": f"C{number}", "verdict": "met", "evidence": [], "gaps": ""}
        for number in range(1, criteria + 1)
    ]
    review = {"criteria": verdicts, "summary": "Strong on the redirect path."}
    return Answer(
        json={
            "content": [{"type": "text", "text": json.dumps(review)}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 9_812, "output_tokens": 2_410},
        }
    )


def test_a_real_child_reaches_the_fake_provider_while_the_server_sends_nothing(
    tmp_path, monkeypatch
):
    """The page's job is a child `cstudy ai review` of the workspace, in its own process, which
    reads the consent the server recorded, sends to the fake provider through
    `CSTUDY_AI_ENDPOINT` and stores the review. The server process runs under the network guard
    and its own models never see a request."""
    config = tmp_path / "config"
    config.mkdir()
    (config / "config.toml").write_text('[ai]\nenabled = true\nmodel = "anthropic:claude-x"\n')
    for name in ("CSTUDY_WORKSPACE", "CSTUDY_CONTENT"):
        monkeypatch.delenv(name, raising=False)
    environ = {"CSTUDY_CONFIG": str(config / "config.toml")}
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    workspace = tmp_path / "workspace"
    created = CliRunner().invoke(cli.app, ["init", str(workspace), "--lang", "python"])
    assert created.exit_code == 0, created.output
    with FakeAiProvider() as provider:
        monkeypatch.setenv(ENDPOINT_VARIABLE, provider.endpoint)
        loaded = load_environment(workspace, environ, tmp_path / "home")
        models = ScriptedLanguageModels()
        environment = replace(loaded, models=models)
        environment.credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
        start_item_attempt(environment, ItemStartRequest(SLUG))
        environment.workspace.write_text(NOTES, ANSWER)
        provider.script(
            Provider.ANTHROPIC,
            Route.COMPLETE,
            review_reply(len(plan_review(environment, SLUG).criteria)),
        )
        (tmp_path / "server").mkdir()
        app = web_app(tmp_path / "server", environment, ChildCommand(), Children(QUICK))
        with session_client(app) as client:
            asked = start(client, REVIEW)
            started = start(client, {**REVIEW, "confirm": True})
            job = started.json()["id"]
            text = client.get(f"{JOBS}/{job}/events").text
            listing = client.get(reviews_of(SLUG)).json()
    closed = [frame.data for frame in frames(text) if frame.event == "closed"]
    output = [line["text"] for line in lines_of(frames(text), "line")]
    assert (error(asked), started.status_code) == ((409, "confirmation_required"), 201)
    assert [entry["exit_code"] for entry in closed] == [0], output
    assert f"AI review · {SLUG} · attempt 1 · anthropic:claude-x · review-1" in output
    assert len(provider.requests_to(Provider.ANTHROPIC, Route.COMPLETE)) == 1
    assert provider.unanswered == []
    assert models.requests == []
    assert models.listed == []
    assert [review["model"] for review in listing["reviews"]] == ["claude-x"]
    assert SECRET not in text + json.dumps(listing) + asked.text + started.text
