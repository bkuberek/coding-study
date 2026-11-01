"""Runs and jobs (docs/specs/web-ui.md#runs-and-jobs): `cstudy test`, `cstudy submit` and the jobs
started as child processes, their documents, their streams and their cancel.

A run's pre-checks are use case calls, so their refusals are HTTP errors with the CLI's words;
once the child starts, everything it says reaches the page through its stream.
"""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.preferences import read_preferences
from coding_study.application.run_checks import (
    RunCheck,
    RunSubject,
    check_run,
    check_verify_scope,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import ProblemKind
from coding_study.entrypoints.web.context import in_workspace, server_state
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.queries import positive_integer
from coding_study.entrypoints.web.responses import JsonResponse, event_stream, json_body
from coding_study.entrypoints.web.run_options import (
    JobCommand,
    JobOptions,
    RunOptions,
    job_options,
    run_options,
)
from coding_study.entrypoints.web.runs import Child, Children, ChildStart

RUNS = "/api/v1/runs"
RUN = f"{RUNS}/{{run_id}}"
JOBS = "/api/v1/jobs"
JOB = f"{JOBS}/{{job_id}}"
DOCTOR_FIX_QUESTION = (
    "Run cstudy doctor --fix? It writes missing workspace files, refreshes the runner runtime, "
    "migrates progress.db, and runs uv sync, pnpm install and the Gradle warm-up, which may "
    "need the network."
)
RUNNING = "running"
ENDED = "ended"

type Lookup = Callable[[Children, str], Child]


async def start_run(request: Request) -> Response:
    options = run_options(await json_body(request))
    subject, workspace = await in_workspace(request, _checked_run, options.check)
    server = server_state(request)
    if options.typecheck is None:
        preferences = await server.worker.run(read_preferences, server.settings.preferences)
        options = replace(options, typecheck=preferences.typecheck)
    start = ChildStart(
        server.settings.child,
        workspace,
        options.arguments(subject),
        options.check.command,
        _run_title(options, subject),
        options.document(),
        attempt_id=options.check.attempt_id,
    )
    run = await server.children.start_run(start)
    return JsonResponse({"id": run.id}, status_code=201)


async def list_runs(request: Request) -> Response:
    attempt_id = positive_integer(request.query_params, "attempt_id")
    if attempt_id is None:
        raise UsageError("attempt_id is required")
    runs = server_state(request).children.runs_of(attempt_id)
    return JsonResponse([_run_document(run) for run in runs])


async def run_document(request: Request) -> Response:
    return JsonResponse(_run_document(_child(request, Children.run)))


async def run_events(request: Request) -> Response:
    return _stream(request, _child(request, Children.run))


async def cancel_run(request: Request) -> Response:
    return _cancel(_child(request, Children.run))


async def start_job(request: Request) -> Response:
    options = job_options(await json_body(request))
    if options.command is JobCommand.DOCTOR_FIX and not options.confirmed:
        raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, DOCTOR_FIX_QUESTION)
    workspace = await in_workspace(request, _checked_job, options)
    server = server_state(request)
    start = ChildStart(
        server.settings.child,
        workspace,
        options.arguments,
        options.command,
        options.title,
        options.document,
        excludes_runs=options.command is JobCommand.DOCTOR_FIX,
    )
    job = await server.children.start_job(start)
    return JsonResponse({"id": job.id}, status_code=201)


async def job_document(request: Request) -> Response:
    return JsonResponse(_job_document(_child(request, Children.job)))


async def job_events(request: Request) -> Response:
    return _stream(request, _child(request, Children.job))


async def cancel_job(request: Request) -> Response:
    return _cancel(_child(request, Children.job))


def run_routes() -> list[BaseRoute]:
    return [
        Route(RUNS, start_run, methods=["POST"]),
        Route(RUNS, list_runs, methods=["GET"]),
        Route(RUN, run_document, methods=["GET"]),
        Route(f"{RUN}/events", run_events, methods=["GET"]),
        Route(f"{RUN}/cancel", cancel_run, methods=["POST"]),
        Route(JOBS, start_job, methods=["POST"]),
        Route(JOB, job_document, methods=["GET"]),
        Route(f"{JOB}/events", job_events, methods=["GET"]),
        Route(f"{JOB}/cancel", cancel_job, methods=["POST"]),
    ]


def _checked_run(environment: Environment, check: RunCheck) -> tuple[RunSubject, Path]:
    return check_run(environment, check), environment.root


def _checked_job(environment: Environment, options: JobOptions) -> Path:
    check_verify_scope(environment, options.slugs)
    return environment.root


def _run_title(options: RunOptions, subject: RunSubject) -> str:
    """`test two-sum · python`; a project's language is its own, as in `cstudy submit`."""
    title = f"{options.check.command} {subject.slug}"
    return title if subject.kind is ProblemKind.PROJECT else f"{title} · {subject.language}"


def _child(request: Request, lookup: Lookup) -> Child:
    child_id: str = request.path_params.get("run_id") or request.path_params["job_id"]
    return lookup(server_state(request).children, child_id)


def _stream(request: Request, child: Child) -> Response:
    return event_stream(request, child.frames)


def _cancel(child: Child) -> Response:
    if not child.running:
        message = f"{child.kind} {child.id} has ended"
        raise ApiError(ErrorCode.CONFLICT, message, {child.kind: child.id})
    child.cancel()
    return JsonResponse({"id": child.id}, status_code=202)


def _run_document(run: Child) -> dict[str, JsonValue]:
    summary = run.run_end.get("summary") if run.run_end else None
    return {
        **_job_document(run),
        "attempt_id": run.start.attempt_id,
        "summary": summary,
    }


def _job_document(child: Child) -> dict[str, JsonValue]:
    return {
        "id": child.id,
        "command": child.start.command,
        "options": dict(child.start.options),
        "state": RUNNING if child.running else ENDED,
        "started_at": child.started_at,
        "exit_code": child.closed.exit_code if child.closed else None,
    }
