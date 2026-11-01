"""`GET /api/v1/session` and the preferences (docs/specs/web-ui.md#session-and-preferences)."""

import json

import pytest

from coding_study.domain.config import Config
from coding_study.domain.jdk import JdkSource
from coding_study.domain.problem import Language
from tests.fakes import FakeJdk, jdk_of
from tests.web_server import (
    PORT,
    TEST_VERSION,
    WRITE_HEADERS,
    session_client,
    web_app,
    web_workspace,
)

PREFERENCES = "/api/v1/preferences"
PREFERENCES_FILE = ".cs/serve/preferences.json"
DEFAULTS = {"format": 1, "vim": False, "run_on_save": False, "typecheck": True, "theme": "system"}


@pytest.fixture
def app(tmp_path):
    return web_app(tmp_path)


def test_the_session_describes_the_server_and_the_workspace(tmp_path, app):
    with session_client(app) as client:
        document = client.get("/api/v1/session").json()
    assert document == {
        "api": 1,
        "cstudy": TEST_VERSION,
        "events_version": 1,
        "workspace": str(tmp_path),
        "port": PORT,
        "default_lang": "python",
        "languages": ["python", "typescript", "java", "kotlin", "go", "rust"],
        "tracks": [
            "dsa",
            "practical",
            "lld",
            "concurrency",
            "debugging",
            "system-design",
            "code-review",
            "behavioral",
        ],
        "kinds": ["function", "design", "progressive", "concurrent", "project", "item"],
        "selected_jdk": {
            "version": "21.0.13",
            "feature": 21,
            "source": "JAVA_HOME",
            "supported": True,
        },
    }


def selected_jdk(tmp_path, jdk):
    environment = web_workspace(tmp_path, jdk=jdk)
    with session_client(web_app(tmp_path, environment)) as client:
        return client.get("/api/v1/session").json()["selected_jdk"]


def test_the_session_names_the_jdk_the_server_selects(tmp_path):
    assert selected_jdk(tmp_path, jdk_of(27, JdkSource.PATH)) == {
        "version": "27.0.1",
        "feature": 27,
        "source": "PATH",
        "supported": False,
    }


def test_the_session_has_no_jdk_when_none_is_found(tmp_path):
    assert selected_jdk(tmp_path, FakeJdk(None)) is None


def test_the_selected_jdk_matches_the_listing_document(tmp_path):
    environment = web_workspace(tmp_path, jdk=jdk_of(26))
    with session_client(web_app(tmp_path, environment)) as client:
        document = client.get("/api/v1/session").json()
        listed = client.get("/api/v1/problems").json()
    assert document["selected_jdk"] == listed["selected_jdk"]


def test_the_session_reads_the_default_language_from_the_config(tmp_path):
    environment = web_workspace(tmp_path, config=Config(default_lang=Language.KOTLIN))
    with session_client(web_app(tmp_path, environment)) as client:
        document = client.get("/api/v1/session").json()
    assert document["default_lang"] == "kotlin"


def test_the_api_answers_json_in_utf8(app):
    with session_client(app) as client:
        response = client.get("/api/v1/session")
    assert response.headers["content-type"] == "application/json; charset=utf-8"


def test_preferences_default_without_a_file(app):
    with session_client(app) as client:
        assert client.get(PREFERENCES).json() == DEFAULTS


def test_saving_preferences_answers_the_stored_document(app):
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={"vim": True}, headers=WRITE_HEADERS)
    assert response.json() == {**DEFAULTS, "vim": True}


def test_saved_preferences_are_read_back(app):
    with session_client(app) as client:
        client.put(PREFERENCES, json={**DEFAULTS, "typecheck": False}, headers=WRITE_HEADERS)
        document = client.get(PREFERENCES).json()
    assert document == {**DEFAULTS, "typecheck": False}


def test_saved_preferences_are_written_to_the_workspace(tmp_path, app):
    with session_client(app) as client:
        client.put(PREFERENCES, json={"run_on_save": True}, headers=WRITE_HEADERS)
    stored = json.loads((tmp_path / PREFERENCES_FILE).read_text())
    assert stored == {**DEFAULTS, "run_on_save": True}


def test_an_unknown_preference_gets_422_usage(app):
    with session_client(app) as client:
        response = client.put(PREFERENCES, json={"font": "serif"}, headers=WRITE_HEADERS)
    assert (response.status_code, response.json()) == (
        422,
        {"error": {"code": "usage", "message": 'unknown preference "font"', "fix": None}},
    )


def test_a_body_that_is_not_json_gets_422_usage(app):
    with session_client(app) as client:
        response = client.put(PREFERENCES, content=b"{vim", headers=WRITE_HEADERS)
    assert (response.status_code, response.json()["error"]["message"]) == (
        422,
        "the request body is not JSON",
    )


def test_an_unreadable_file_reads_as_the_defaults(tmp_path, app):
    (tmp_path / PREFERENCES_FILE).parent.mkdir(parents=True)
    (tmp_path / PREFERENCES_FILE).write_text("{not json")
    with session_client(app) as client:
        assert client.get(PREFERENCES).json() == DEFAULTS
