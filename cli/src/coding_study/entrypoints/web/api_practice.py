"""Starting an attempt, revealing its hints and finishing or aborting it
(docs/specs/web-ui.md#attempts), through the use cases `cstudy start --no-open`, `cstudy hint`,
`cstudy done` and `cstudy abort` call. Hints, done and abort address the attempt by its id and call
the use case with its slug and language."""

from dataclasses import replace

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.adapters.ide.generated_files import FsGeneratedFiles
from coding_study.adapters.run_activity import ProcessRunActivity
from coding_study.application.abort_attempt import abort_attempt
from coding_study.application.active_attempt import attempt_in_progress
from coding_study.application.attempt_status import attempt_status
from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.environment import Environment
from coding_study.application.ide_files import link_rust_projects
from coding_study.application.practice_catalog import is_item
from coding_study.application.reveal_hint import reveal_hint
from coding_study.application.start_attempt import StartedAttempt, StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import SECONDS_PER_MINUTE, Attempt, Rating
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.entrypoints.commands.abort import abort_question
from coding_study.entrypoints.commands.ide import RENDERERS
from coding_study.entrypoints.commands.status import status_document
from coding_study.entrypoints.web.api_attempts import ATTEMPT
from coding_study.entrypoints.web.bodies import (
    object_body,
    optional_choice,
    optional_integer,
    optional_text,
    required_text,
    switch,
)
from coding_study.entrypoints.web.context import in_workspace, server_state
from coding_study.entrypoints.web.documents import abort_document, done_document, hint_document
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.responses import JsonResponse

ATTEMPTS = "/api/v1/attempts"
ABORT_COMMAND = "cstudy abort"
CREATED = 201
TIMER_MINUTES = (1, 600)


async def start(request: Request) -> Response:
    """`cstudy start <slug> --no-open [--lang] [--fresh] [--timer <n>m]`: starts or resumes."""
    body = await object_body(request)
    minutes = optional_integer(body, "timer_minutes", TIMER_MINUTES)
    start_request = StartRequest(
        slug=required_text(body, "slug"),
        language=optional_choice(body, "language", Language),
        fresh=switch(body, "fresh"),
        timer_s=None if minutes is None else minutes * SECONDS_PER_MINUTE,
    )
    document = await in_workspace(request, _start, start_request)
    return JsonResponse(document, status_code=CREATED)


async def hint(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _hint, _attempt_id(request)))


async def abort(request: Request) -> Response:
    """`cstudy abort`: the question first, then no run or job during the abort."""
    body = await object_body(request)
    server = server_state(request)
    async with server.children.none_running(ABORT_COMMAND):
        document = await in_workspace(
            request, _abort, _attempt_id(request), switch(body, "confirm")
        )
    return JsonResponse(document)


async def done(request: Request) -> Response:
    body = await object_body(request)
    done_request = DoneRequest(
        rating=optional_choice(body, "rating", Rating),
        gave_up=switch(body, "gave_up"),
        notes=optional_text(body, "notes"),
    )
    return JsonResponse(await in_workspace(request, _done, _attempt_id(request), done_request))


def practice_routes() -> list[BaseRoute]:
    return [
        Route(ATTEMPTS, start, methods=["POST"]),
        Route(f"{ATTEMPT}/hints", hint, methods=["POST"]),
        Route(f"{ATTEMPT}/done", done, methods=["POST"]),
        Route(f"{ATTEMPT}/abort", abort, methods=["POST"]),
    ]


def _attempt_id(request: Request) -> int:
    return request.path_params["attempt_id"]


def _start(environment: Environment, request: StartRequest) -> dict[str, JsonValue]:
    attempt = (
        _start_item(environment, request)
        if is_item(environment, request.slug)
        else _start_problem(environment, request)
    )
    return status_document(attempt_status(environment, attempt.slug, attempt.language))


def _start_problem(environment: Environment, request: StartRequest) -> Attempt:
    started = start_attempt(environment, request)
    if _seeded_rust_folder(started):
        link_rust_projects(RENDERERS, FsGeneratedFiles(environment.root))
    return started.attempt


def _seeded_rust_folder(started: StartedAttempt) -> bool:
    """A Rust project folder this start wrote, which VS Code's settings then link, as
    `cstudy start` links it."""
    language = started.attempt.language
    return started.project is not None and started.created_stub and language is Language.RUST


def _start_item(environment: Environment, request: StartRequest) -> Attempt:
    """Items take no language: their answer is a notes file."""
    if request.language is not None:
        raise UsageError(f"{request.slug} is not autograded; --lang applies to problems")
    item_request = ItemStartRequest(request.slug, request.fresh, request.timer_s)
    return start_item_attempt(environment, item_request).attempt


def _hint(environment: Environment, attempt_id: int) -> dict[str, JsonValue]:
    attempt = attempt_in_progress(environment.progress, attempt_id)
    return hint_document(reveal_hint(environment, attempt.slug, attempt.language))


def _done(environment: Environment, attempt_id: int, request: DoneRequest) -> dict[str, JsonValue]:
    attempt = attempt_in_progress(environment.progress, attempt_id)
    addressed = replace(request, slug=attempt.slug, language=attempt.language)
    return done_document(complete_attempt(environment, addressed))


def _abort(environment: Environment, attempt_id: int, confirmed: bool) -> dict[str, JsonValue]:
    attempt = attempt_in_progress(environment.progress, attempt_id)
    if not confirmed:
        raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, abort_question(attempt))
    activity = ProcessRunActivity(environment.root)
    return abort_document(abort_attempt(environment, attempt, activity))
