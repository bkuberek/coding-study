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
from coding_study.entrypoints.web.errors import (
    ErrorCode,
    domain_error_code,
    error_status,
    split_fix,
)
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


# the CLI's `fix:` hint

JDK_REFUSAL = "two-sum runs its java version on JDK 21 to 26; JAVA_HOME selects JDK 27"
JDK_FIX = "select a JDK 21 to 26 with JAVA_HOME, or install JDK 25: https://example.org/guide#jdk"


def test_a_refusal_with_a_fix_line_puts_the_hint_in_the_fix_field(tmp_path):
    response = session_error(tmp_path, RunnerStartError(JDK_REFUSAL, (f"fix: {JDK_FIX}",)))
    assert (response.status_code, response.json()["error"]) == (
        503,
        {"code": "environment", "message": JDK_REFUSAL, "fix": JDK_FIX},
    )


def test_a_refusal_without_a_fix_line_keeps_fix_null(tmp_path):
    response = session_error(tmp_path, RunnerStartError("the runner said nothing"))
    assert response.json()["error"]["fix"] is None


def test_the_lines_before_the_fix_line_stay_in_the_message(tmp_path):
    error = RunnerStartError("no hello", ("runner: boom", "fix: reinstall"))
    response = session_error(tmp_path, error)
    assert response.json()["error"] == {
        "code": "environment",
        "message": "no hello\nrunner: boom",
        "fix": "reinstall",
    }


@pytest.mark.parametrize(
    ("text", "message", "fix"),
    [
        ("no pnpm\nfix: brew install pnpm", "no pnpm", "brew install pnpm"),
        ("no pnpm", "no pnpm", None),
        ("a\nb\nfix: c", "a\nb", "c"),
        ("a; fix: b", "a; fix: b", None),
        ("a\nfix: b\nmore", "a\nfix: b\nmore", None),
        ("fix: alone", "fix: alone", None),
        ("a\nfix: ", "a\nfix: ", None),
        ("a\nfix: x\nfix: y", "a\nfix: x", "y"),
    ],
)
def test_only_a_trailing_fix_line_is_split_off(text, message, fix):
    assert split_fix(text) == (message, fix)
