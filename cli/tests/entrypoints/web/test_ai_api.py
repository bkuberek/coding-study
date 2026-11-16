"""The AI preview's endpoints (docs/specs/web-ui.md#ai-preview): status, usage, the keys and the
consents, over fakes and over a real `credentials.toml`. A key is in no response and no log line."""

import json
import logging
import stat
from datetime import timedelta

import pytest
from jsonschema import Draft202012Validator

from coding_study.adapters.toml_credentials import open_credentials
from coding_study.application.ai_status import ai_status
from coding_study.application.ai_usage import usage_report
from coding_study.domain.ai import AiTask, ApiKey, ModelRef, Provider, Routing
from coding_study.domain.ai_records import CallOutcome, Consent, ModelCall
from coding_study.domain.config import AiSettings, Config
from coding_study.entrypoints.commands.ai_report import status_document, usage_document
from tests.fakes import NOW, FakeAiStore, FakeCredentials
from tests.helpers import SCHEMAS_DIRECTORY
from tests.web_server import WRITE_HEADERS, session_client, web_app, web_workspace

STATUS = "/api/v1/ai/status"
USAGE = "/api/v1/ai/usage"
CONSENTS = "/api/v1/ai/consents"
SECRET = "sk-sentinel-0123456789"
ANTHROPIC = ModelRef(Provider.ANTHROPIC, "claude-x")
OPENROUTER = ModelRef(Provider.OPENROUTER, "vendor/model")
AUTO = AiSettings(enabled=True, routing=Routing.AUTO, fast=OPENROUTER, strong=ANTHROPIC)
CONSENT = {"provider": "anthropic", "model": "claude-x", "purpose": "review"}


def keys(provider: str) -> str:
    return f"/api/v1/ai/keys/{provider}"


def make(root, settings: AiSettings = AUTO, **overrides):
    parts = {
        "config": Config(ai=settings),
        "ai_store": FakeAiStore(),
        "credentials": FakeCredentials(),
    }
    return web_workspace(root, **{**parts, **overrides})


def served(root, settings: AiSettings = AUTO, **overrides):
    environment = make(root, settings, **overrides)
    return environment, web_app(root, environment)


def schema_problems(name: str, document) -> list[str]:
    schema = json.loads((SCHEMAS_DIRECTORY / "cli" / f"{name}.schema.json").read_text())
    return [error.message for error in Draft202012Validator(schema).iter_errors(document)]


def call(day, tokens: int = 1_000) -> ModelCall:
    return ModelCall(
        AiTask.REVIEW,
        Provider.ANTHROPIC,
        "claude-x",
        None,
        None,
        day,
        NOW,
        NOW,
        CallOutcome.OK,
        None,
        tokens,
        tokens // 2,
        tokens + tokens // 2,
        0.25,
    )


def error_of(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


# Status


def test_the_status_is_the_document_of_cstudy_ai_status(tmp_path):
    environment, app = served(tmp_path)
    environment.credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    with session_client(app) as client:
        response = client.get(STATUS)
    document = response.json()
    assert (response.status_code, document) == (200, status_document(ai_status(environment)))
    assert (document["credentials"]["keys"], len(document["consents"])) == (
        {"anthropic": True, "google": False, "openai": False, "openrouter": False},
        1,
    )
    assert schema_problems("ai-status", document) == []


def test_the_status_works_with_ai_off(tmp_path):
    _, app = served(tmp_path, AiSettings())
    with session_client(app) as client:
        document = client.get(STATUS).json()
    assert (document["enabled"], [task["ready"] for task in document["tasks"]]) == (
        False,
        [False, False],
    )
    assert schema_problems("ai-status", document) == []


def test_the_status_reports_a_credentials_file_that_does_not_load(tmp_path, tmp_path_factory):
    config = tmp_path_factory.mktemp("config")
    (config / "credentials.toml").write_text(f'[antropic]\napi_key = "{SECRET}"\n')
    credentials = open_credentials(
        {"CSTUDY_CONFIG": str(config / "config.toml")}, tmp_path, tmp_path
    )
    app = web_app(tmp_path, make(tmp_path, credentials=credentials))
    with session_client(app) as client:
        response = client.get(STATUS)
    assert response.status_code == 200
    assert "unknown provider" in response.json()["credentials"]["issue"]
    assert SECRET not in response.text


# Usage


def test_the_usage_is_the_document_of_cstudy_ai_usage_for_7_days(tmp_path):
    environment, app = served(tmp_path)
    today = environment.clock.local_date(environment.clock.now())
    environment.ai_store.record_call(call(today))
    environment.ai_store.record_call(call(today - timedelta(days=3), 400))
    environment.ai_store.record_call(call(today - timedelta(days=9)))
    with session_client(app) as client:
        response = client.get(USAGE)
    document = response.json()
    assert (response.status_code, document) == (200, usage_document(usage_report(environment, 7)))
    assert (document["days"], len(document["rows"])) == (7, 2)
    assert schema_problems("ai-usage", document) == []


def test_the_usage_takes_the_days(tmp_path):
    environment, app = served(tmp_path)
    today = environment.clock.local_date(environment.clock.now())
    environment.ai_store.record_call(call(today - timedelta(days=9)))
    with session_client(app) as client:
        wide = client.get(USAGE, params={"days": 366}).json()
        narrow = client.get(USAGE, params={"days": 1}).json()
    assert (wide, narrow) == (
        usage_document(usage_report(environment, 366)),
        usage_document(usage_report(environment, 1)),
    )
    assert (len(wide["rows"]), len(narrow["rows"])) == (1, 0)


@pytest.mark.parametrize("days", ["0", "367", "-1", "x", "", "1.5"])
def test_the_usage_refuses_days_outside_1_to_366(tmp_path, days):
    _, app = served(tmp_path)
    with session_client(app) as client:
        response = client.get(USAGE, params={"days": days})
    assert error_of(response) == (422, "usage")
    assert "from 1 to 366" in response.json()["error"]["message"]


# Keys


def test_a_key_is_saved_and_the_answer_says_only_that_it_is_set(tmp_path):
    environment, app = served(tmp_path)
    with session_client(app) as client:
        response = client.put(keys("anthropic"), json={"key": SECRET}, headers=WRITE_HEADERS)
        status = client.get(STATUS)
    assert (response.status_code, response.json()) == (
        200,
        {"provider": "anthropic", "set": True},
    )
    assert environment.credentials.keys_set() == {Provider.ANTHROPIC}
    assert status.json()["credentials"]["keys"]["anthropic"] is True
    assert SECRET not in response.text + status.text


def test_a_key_is_never_in_a_response_a_header_or_a_log_line(tmp_path, caplog):
    _, app = served(tmp_path)
    with caplog.at_level(logging.DEBUG), session_client(app) as client:
        responses = [
            client.put(keys("anthropic"), json={"key": SECRET}, headers=WRITE_HEADERS),
            client.put(keys("anthropic"), json={"key": f"{SECRET} x"}, headers=WRITE_HEADERS),
            client.put(keys("nothing"), json={"key": SECRET}, headers=WRITE_HEADERS),
            client.put(keys("anthropic"), json={"key": [SECRET]}, headers=WRITE_HEADERS),
            client.put(keys("anthropic"), content=f'{{"key": "{SECRET}"', headers=WRITE_HEADERS),
            client.get(STATUS),
            client.get(USAGE),
        ]
    shown = "".join(f"{response.headers}{response.text}" for response in responses) + caplog.text
    assert SECRET not in shown


def test_a_key_over_a_real_file_is_found_again_and_the_file_goes_with_its_last_key(
    tmp_path, tmp_path_factory
):
    config = tmp_path_factory.mktemp("config")
    root = tmp_path / "workspace"
    root.mkdir()
    credentials = open_credentials({"CSTUDY_CONFIG": str(config / "config.toml")}, tmp_path, root)
    app = web_app(root, make(root, credentials=credentials))
    file = config / "credentials.toml"
    with session_client(app) as client:
        saved = client.put(keys("openai"), json={"key": SECRET}, headers=WRITE_HEADERS)
        status = client.get(STATUS).json()
        removed = client.delete(keys("openai"), headers=WRITE_HEADERS)
    assert (saved.status_code, status["credentials"]["keys"]["openai"]) == (200, True)
    assert (removed.json(), file.exists()) == ({"provider": "openai", "set": False}, False)


def test_the_file_a_key_goes_to_is_private(tmp_path, tmp_path_factory):
    config = tmp_path_factory.mktemp("config")
    root = tmp_path / "workspace"
    root.mkdir()
    credentials = open_credentials({"CSTUDY_CONFIG": str(config / "config.toml")}, tmp_path, root)
    app = web_app(root, make(root, credentials=credentials))
    with session_client(app) as client:
        client.put(keys("openai"), json={"key": SECRET}, headers=WRITE_HEADERS)
    file = config / "credentials.toml"
    assert (stat.S_IMODE(file.stat().st_mode), f'api_key = "{SECRET}"' in file.read_text()) == (
        0o600,
        True,
    )


def test_a_key_for_an_unknown_provider_is_not_found(tmp_path):
    environment, app = served(tmp_path)
    with session_client(app) as client:
        put = client.put(keys("nothing"), json={"key": SECRET}, headers=WRITE_HEADERS)
        delete = client.delete(keys("nothing"), headers=WRITE_HEADERS)
    assert (error_of(put), error_of(delete)) == ((404, "not_found"), (404, "not_found"))
    assert environment.credentials.keys_set() == frozenset()


@pytest.mark.parametrize(
    "body",
    [{}, {"key": None}, {"key": 5}, {"key": ""}, {"key": "two words"}, {"key": "tab\there"}, []],
)
def test_a_key_the_cli_refuses_is_422_and_changes_nothing(tmp_path, body):
    environment, app = served(tmp_path)
    with session_client(app) as client:
        response = client.put(keys("google"), json=body, headers=WRITE_HEADERS)
    assert error_of(response) == (422, "usage")
    assert environment.credentials.keys_set() == frozenset()


def test_a_body_that_is_not_json_is_422(tmp_path):
    _, app = served(tmp_path)
    with session_client(app) as client:
        response = client.put(keys("google"), content="sk-nothing", headers=WRITE_HEADERS)
    assert error_of(response) == (422, "usage")


def test_a_file_inside_the_workspace_is_refused_with_the_cli_message(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "config.toml").write_text("")
    credentials = open_credentials({"CSTUDY_CONFIG": str(root / "config.toml")}, tmp_path, root)
    app = web_app(root, make(root, credentials=credentials))
    with session_client(app) as client:
        response = client.put(keys("anthropic"), json={"key": SECRET}, headers=WRITE_HEADERS)
    assert error_of(response) == (422, "usage")
    assert (SECRET in response.text, (root / "credentials.toml").exists()) == (False, False)


def test_a_file_that_does_not_load_is_503_and_left_as_it_was(tmp_path, tmp_path_factory):
    config = tmp_path_factory.mktemp("config")
    file = config / "credentials.toml"
    file.write_text('[antropic]\napi_key = "kept"\n')
    credentials = open_credentials(
        {"CSTUDY_CONFIG": str(config / "config.toml")}, tmp_path, tmp_path
    )
    app = web_app(tmp_path, make(tmp_path, credentials=credentials))
    with session_client(app) as client:
        put = client.put(keys("anthropic"), json={"key": SECRET}, headers=WRITE_HEADERS)
        delete = client.delete(keys("anthropic"), headers=WRITE_HEADERS)
    assert (error_of(put), error_of(delete)) == ((503, "environment"), (503, "environment"))
    assert (file.read_text(), SECRET in put.text + delete.text) == (
        '[antropic]\napi_key = "kept"\n',
        False,
    )


def test_a_key_is_removed(tmp_path):
    environment, app = served(tmp_path)
    environment.credentials.save_key(Provider.GOOGLE, ApiKey(SECRET))
    with session_client(app) as client:
        response = client.delete(keys("google"), headers=WRITE_HEADERS)
        status = client.get(STATUS).json()
    assert (response.status_code, response.json()) == (200, {"provider": "google", "set": False})
    assert (environment.credentials.keys_set(), status["credentials"]["keys"]["google"]) == (
        frozenset(),
        False,
    )


def test_removing_a_key_that_is_not_set_answers_the_same(tmp_path):
    _, app = served(tmp_path)
    with session_client(app) as client:
        response = client.delete(keys("google"), headers=WRITE_HEADERS)
    assert (response.status_code, response.json()) == (200, {"provider": "google", "set": False})


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH"])
def test_a_key_has_no_other_method(tmp_path, method):
    _, app = served(tmp_path)
    with session_client(app) as client:
        response = client.request(method, keys("anthropic"), headers=WRITE_HEADERS)
    assert error_of(response) == (405, "method_not_allowed")


# Consents


def test_a_consent_is_revoked(tmp_path):
    environment, app = served(tmp_path)
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    with session_client(app) as client:
        first = client.request("DELETE", CONSENTS, json=CONSENT, headers=WRITE_HEADERS)
        again = client.request("DELETE", CONSENTS, json=CONSENT, headers=WRITE_HEADERS)
        status = client.get(STATUS).json()
    assert (first.json(), again.json()) == ({"revoked": True}, {"revoked": False})
    assert (environment.ai_store.consents(), status["consents"]) == ((), [])


def test_revoking_one_consent_keeps_the_others(tmp_path):
    environment, app = served(tmp_path)
    for purpose in AiTask:
        environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", purpose, NOW))
    with session_client(app) as client:
        client.request("DELETE", CONSENTS, json=CONSENT, headers=WRITE_HEADERS)
    assert [consent.purpose for consent in environment.ai_store.consents()] == [AiTask.CHECK]


def test_a_model_id_may_hold_colons_and_slashes(tmp_path):
    environment, app = served(tmp_path)
    environment.ai_store.grant_consent(
        Consent(Provider.OPENROUTER, "vendor/m:free", AiTask.CHECK, NOW)
    )
    body = {"provider": "openrouter", "model": "vendor/m:free", "purpose": "check"}
    with session_client(app) as client:
        response = client.request("DELETE", CONSENTS, json=body, headers=WRITE_HEADERS)
    assert response.json() == {"revoked": True}


@pytest.mark.parametrize(
    "change",
    [
        {"provider": "nothing"},
        {"purpose": "chat"},
        {"model": ""},
        {"model": "two words"},
        {"provider": None},
        {"model": 3},
        {"purpose": None},
    ],
)
def test_a_consent_the_cli_would_refuse_is_422(tmp_path, change):
    environment, app = served(tmp_path)
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    with session_client(app) as client:
        response = client.request(
            "DELETE", CONSENTS, json={**CONSENT, **change}, headers=WRITE_HEADERS
        )
    assert error_of(response) == (422, "usage")
    assert len(environment.ai_store.consents()) == 1


def test_revoking_with_ai_off_works(tmp_path):
    environment, app = served(tmp_path, AiSettings())
    environment.ai_store.grant_consent(Consent(Provider.ANTHROPIC, "claude-x", AiTask.REVIEW, NOW))
    with session_client(app) as client:
        response = client.request("DELETE", CONSENTS, json=CONSENT, headers=WRITE_HEADERS)
    assert response.json() == {"revoked": True}


# The session


@pytest.mark.parametrize("enabled", [False, True])
def test_the_session_says_whether_ai_is_on(tmp_path, enabled):
    _, app = served(tmp_path, AiSettings(enabled=enabled))
    with session_client(app) as client:
        document = client.get("/api/v1/session").json()
    assert document["ai"] == {"enabled": enabled}
