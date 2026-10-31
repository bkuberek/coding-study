"""The API's one error document and its codes (docs/specs/web-ui.md#api-conventions):

    {"error": {"code": "usage", "message": "level 3 is locked; ...", "fix": null}}

A use case's error gets the code of the exit code the CLI gives it, so the page refuses what the
terminal refuses, with the same message. A bug is `internal`; its traceback goes to the server's
standard error, never into the response.
"""

from collections.abc import Mapping
from enum import StrEnum

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ExceptionHandler

from coding_study.domain.errors import (
    AttemptEndedError,
    UnknownAttemptError,
    UnknownFileError,
    UnknownProblemError,
)
from coding_study.entrypoints.shared import ERROR_EXIT_CODES, ExitCode
from coding_study.entrypoints.web.responses import JsonResponse


class ErrorCode(StrEnum):
    USAGE = "usage"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    ATTEMPT_ENDED = "attempt_ended"
    CONFLICT = "conflict"
    LOCKED = "locked"
    CONFIRMATION_REQUIRED = "confirmation_required"
    PRECONDITION_FAILED = "precondition_failed"
    PRECONDITION_REQUIRED = "precondition_required"
    TOO_LARGE = "too_large"
    ENVIRONMENT = "environment"
    CONTENT = "content"
    INTERNAL = "internal"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"


_STATUSES: Mapping[ErrorCode, int] = {
    ErrorCode.USAGE: 422,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.ATTEMPT_ENDED: 409,
    ErrorCode.CONFLICT: 409,
    ErrorCode.LOCKED: 409,
    ErrorCode.CONFIRMATION_REQUIRED: 409,
    ErrorCode.PRECONDITION_FAILED: 412,
    ErrorCode.PRECONDITION_REQUIRED: 428,
    ErrorCode.TOO_LARGE: 413,
    ErrorCode.ENVIRONMENT: 503,
    ErrorCode.CONTENT: 500,
    ErrorCode.INTERNAL: 500,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
}
_EXIT_CODE_ERRORS: Mapping[ExitCode, ErrorCode] = {
    ExitCode.USAGE_ERROR: ErrorCode.USAGE,
    ExitCode.ENVIRONMENT_ERROR: ErrorCode.ENVIRONMENT,
    ExitCode.CONTENT_ERROR: ErrorCode.CONTENT,
    ExitCode.INTERNAL_ERROR: ErrorCode.INTERNAL,
}
_HTTP_ERRORS: Mapping[int, ErrorCode] = {
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
}
_LOOKUP_ERRORS: Mapping[type[Exception], ErrorCode] = {
    UnknownProblemError: ErrorCode.NOT_FOUND,
    UnknownAttemptError: ErrorCode.NOT_FOUND,
    UnknownFileError: ErrorCode.NOT_FOUND,
    AttemptEndedError: ErrorCode.ATTEMPT_ENDED,
}
"""Errors whose code is not their exit code's: what the API addresses that is missing or over."""
INTERNAL_MESSAGE = "internal error; the terminal running cstudy serve shows its traceback"


class ApiError(Exception):
    """A refusal no use case raises, such as a child `cstudy` that failed or ran too long."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def error_status(code: ErrorCode) -> int:
    return _STATUSES[code]


def error_response(
    code: ErrorCode, message: str, headers: Mapping[str, str] | None = None
) -> JsonResponse:
    document = {"error": {"code": code.value, "message": message, "fix": None}}
    return JsonResponse(document, status_code=error_status(code), headers=headers)


def domain_error_code(error: Exception) -> ErrorCode:
    """The code of the exit code the CLI gives `error`, but `not_found` for an unknown problem,
    attempt or file and `attempt_ended` for an attempt no longer in progress."""
    code = _LOOKUP_ERRORS.get(type(error))
    return code if code is not None else _EXIT_CODE_ERRORS[ERROR_EXIT_CODES[type(error)]]


def exit_code_error(exit_code: int) -> ErrorCode:
    """The code of a child `cstudy`'s exit code; `internal` for one the CLI does not document."""
    try:
        return _EXIT_CODE_ERRORS[ExitCode(exit_code)]
    except (ValueError, KeyError):
        return ErrorCode.INTERNAL


async def _domain_error(_request: Request, error: Exception) -> Response:
    return error_response(domain_error_code(error), str(error))


async def _api_error(_request: Request, error: Exception) -> Response:
    assert isinstance(error, ApiError)
    return error_response(error.code, str(error))


async def _http_error(request: Request, error: Exception) -> Response:
    assert isinstance(error, HTTPException)
    code = _HTTP_ERRORS.get(error.status_code, ErrorCode.INTERNAL)
    if code is ErrorCode.NOT_FOUND:
        return error_response(code, f"not found: {request.url.path}")
    return error_response(
        code, f"{request.method} {request.url.path}: {error.detail}", error.headers
    )


async def _internal_error(_request: Request, _error: Exception) -> Response:
    """Starlette re-raises the error after this response, and uvicorn prints its traceback."""
    return error_response(ErrorCode.INTERNAL, INTERNAL_MESSAGE)


def exception_handlers() -> dict[type[Exception], ExceptionHandler]:
    return {
        **dict.fromkeys(ERROR_EXIT_CODES, _domain_error),
        **dict.fromkeys(_LOOKUP_ERRORS, _domain_error),
        ApiError: _api_error,
        HTTPException: _http_error,
        Exception: _internal_error,
    }
