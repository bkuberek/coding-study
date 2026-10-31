"""The error document and codes of docs/specs/web-ui.md#api-conventions."""

import pytest

from coding_study.adapters.locations import WorkspaceError
from coding_study.domain.errors import (
    ConfigError,
    ContentError,
    ContentIssue,
    LanguageNotSetUpError,
    RunnerProtocolError,
    RunnerStartError,
    UnknownProblemError,
    UsageError,
    VersionControlError,
)
from coding_study.entrypoints.web.errors import ErrorCode, domain_error_code, error_status
from tests.web_server import WRITE_HEADERS, session_client, web_app


class BrokenEnvironment:
    """An environment whose loading fails with `error`, as a use case's would."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    @property
    def root(self):
        raise self.error

    @property
    def config(self):
        raise self.error


def session_error(tmp_path, error: Exception):
    app = web_app(tmp_path, BrokenEnvironment(error))  # type: ignore[arg-type]
    with session_client(app) as client:
        return client.get("/api/v1/session")


def test_an_unknown_endpoint_gets_404_not_found(tmp_path):
    with session_client(web_app(tmp_path)) as client:
        response = client.get("/api/v1/nothing")
    assert response.json() == {
        "error": {"code": "not_found", "message": "not found: /api/v1/nothing", "fix": None}
    }


def test_a_method_an_endpoint_lacks_gets_405_naming_the_ones_it_has(tmp_path):
    with session_client(web_app(tmp_path)) as client:
        response = client.delete("/api/v1/session", headers=WRITE_HEADERS)
    allowed = set(response.headers["allow"].split(", "))
    assert (response.status_code, response.json()["error"]["code"], allowed) == (
        405,
        "method_not_allowed",
        {"GET", "HEAD"},
    )


def test_a_usage_error_gets_422_with_the_clis_message(tmp_path):
    response = session_error(tmp_path, UsageError("level 3 is locked"))
    assert (response.status_code, response.json()["error"]) == (
        422,
        {"code": "usage", "message": "level 3 is locked", "fix": None},
    )


def test_a_bug_gets_500_internal_without_a_traceback(tmp_path):
    response = session_error(tmp_path, RuntimeError("secret detail"))
    assert (response.status_code, response.json()["error"]) == (
        500,
        {
            "code": "internal",
            "message": "internal error; the terminal running cstudy serve shows its traceback",
            "fix": None,
        },
    )


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (UsageError("no"), ErrorCode.USAGE),
        (WorkspaceError("gone"), ErrorCode.USAGE),
        (UnknownProblemError("nope"), ErrorCode.NOT_FOUND),
        (ContentError([ContentIssue("meta.yaml", "id", "missing")]), ErrorCode.CONTENT),
        (ConfigError("config.toml", ["bad"]), ErrorCode.ENVIRONMENT),
        (LanguageNotSetUpError("rust", "runner"), ErrorCode.ENVIRONMENT),
        (RunnerStartError("no hello"), ErrorCode.ENVIRONMENT),
        (VersionControlError("no git"), ErrorCode.ENVIRONMENT),
        (RunnerProtocolError("bad line"), ErrorCode.INTERNAL),
    ],
)
def test_a_domain_error_gets_the_code_of_its_exit_code(error, code):
    assert domain_error_code(error) is code


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (ErrorCode.USAGE, 422),
        (ErrorCode.NOT_FOUND, 404),
        (ErrorCode.ATTEMPT_ENDED, 409),
        (ErrorCode.CONFLICT, 409),
        (ErrorCode.LOCKED, 409),
        (ErrorCode.CONFIRMATION_REQUIRED, 409),
        (ErrorCode.PRECONDITION_FAILED, 412),
        (ErrorCode.PRECONDITION_REQUIRED, 428),
        (ErrorCode.TOO_LARGE, 413),
        (ErrorCode.ENVIRONMENT, 503),
        (ErrorCode.CONTENT, 500),
        (ErrorCode.INTERNAL, 500),
        (ErrorCode.UNAUTHORIZED, 401),
        (ErrorCode.FORBIDDEN, 403),
        (ErrorCode.METHOD_NOT_ALLOWED, 405),
    ],
)
def test_each_code_has_the_specs_status(code, status):
    assert error_status(code) == status


def test_a_working_session_is_not_an_error(tmp_path):
    with session_client(web_app(tmp_path)) as client:
        assert client.get("/api/v1/session").status_code == 200
