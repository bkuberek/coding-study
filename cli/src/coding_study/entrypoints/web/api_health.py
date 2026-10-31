"""`GET /api/v1/doctor`: the checks of `cstudy doctor --json`, from a child process, since the
runner handshakes can take a JVM build (docs/specs/web-ui.md#mock-progress-and-health)."""

import json
from pathlib import Path
from typing import cast

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.entrypoints.shared import ERROR_PREFIX, ExitCode
from coding_study.entrypoints.web.children import ChildDeadlineError, ChildResult, run_child
from coding_study.entrypoints.web.context import in_workspace, server_state
from coding_study.entrypoints.web.errors import ApiError, ErrorCode, exit_code_error
from coding_study.entrypoints.web.responses import JsonResponse

DOCTOR = ("doctor", "--json")
DOCTOR_DEADLINE_S = 180
DOCUMENT_EXIT_CODES = frozenset({ExitCode.SUCCESS, ExitCode.ENVIRONMENT_ERROR})
"""`cstudy doctor --json` prints its document whether every check passed (0) or one failed (4)."""


async def doctor(request: Request) -> Response:
    workspace = await in_workspace(request, _root)
    child = server_state(request).settings.child
    try:
        result = await run_child(child, workspace, DOCTOR, DOCTOR_DEADLINE_S)
    except ChildDeadlineError:
        message = f"cstudy {' '.join(DOCTOR)} did not finish within {DOCTOR_DEADLINE_S} s"
        raise ApiError(ErrorCode.ENVIRONMENT, message) from None
    return JsonResponse(_document(result))


def health_routes() -> list[BaseRoute]:
    return [Route("/api/v1/doctor", doctor, methods=["GET"])]


def _root(environment: Environment) -> Path:
    return environment.root


def _document(result: ChildResult) -> dict[str, object]:
    """The child's document; its error, by its exit code, when it printed none."""
    if result.exit_code in DOCUMENT_EXIT_CODES:
        try:
            document: object = json.loads(result.stdout)
        except ValueError:
            document = None
        if isinstance(document, dict):
            return cast(dict[str, object], document)
    raise ApiError(exit_code_error(result.exit_code), _message(result))


def _message(result: ChildResult) -> str:
    """The child's error line without its `error: ` prefix."""
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    if not lines:
        return f"cstudy {' '.join(DOCTOR)} exited {result.exit_code}"
    return lines[-1].removeprefix(ERROR_PREFIX)
