"""The dev stack of a service project from the page (docs/specs/web-ui.md#dev-stack): a child
`cstudy dev <slug> --events`, one per attempt, its stream, its stop, and each scenario switch as a
line on its standard input, which `cstudy dev` checks against the scenarios its stack holds.
"""

import json
from pathlib import Path

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.run_checks import check_dev
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.web.bodies import object_body, required_integer
from coding_study.entrypoints.web.context import in_workspace, server_state
from coding_study.entrypoints.web.queries import positive_integer
from coding_study.entrypoints.web.responses import JsonResponse, event_stream
from coding_study.entrypoints.web.runs import Child, ChildStart

DEVS = "/api/v1/dev"
DEV = f"{DEVS}/{{dev_id}}"
DEV_COMMAND = "dev"
RUNNING = "running"
ENDED = "ended"
SWITCH_FIELDS = ("mock", "scenario")


async def start_dev(request: Request) -> Response:
    attempt_id = required_integer(await object_body(request), "attempt_id")
    slug, workspace = await in_workspace(request, _checked_dev, attempt_id)
    server = server_state(request)
    start = ChildStart(
        server.settings.child,
        workspace,
        (DEV_COMMAND, slug, "--events"),
        DEV_COMMAND,
        f"dev {slug}",
        attempt_id=attempt_id,
    )
    dev = await server.children.start_dev(start)
    return JsonResponse({"id": dev.id}, status_code=201)


async def list_devs(request: Request) -> Response:
    attempt_id = positive_integer(request.query_params, "attempt_id")
    if attempt_id is None:
        raise UsageError("attempt_id is required")
    devs = server_state(request).children.devs_of(attempt_id)
    return JsonResponse([_document(dev) for dev in devs])


async def dev_document(request: Request) -> Response:
    return JsonResponse(_document(_dev(request)))


async def dev_events(request: Request) -> Response:
    return event_stream(request, _dev(request).frames)


async def stop_dev(request: Request) -> Response:
    """As Ctrl-C in a terminal: the stack comes down and keeps its data."""
    dev = _dev(request)
    dev.cancel()
    return JsonResponse({"id": dev.id}, status_code=202)


async def switch_scenario(request: Request) -> Response:
    """`{"mock", "scenario"}`, `scenario` null for none; `cstudy dev` answers with a `scenario`
    event, which says why it refused one."""
    body = await object_body(request)
    unknown = sorted(set(body) - set(SWITCH_FIELDS))
    mock, scenario = body.get("mock"), body.get("scenario")
    if unknown or not isinstance(mock, str) or not (scenario is None or isinstance(scenario, str)):
        raise UsageError('a switch is {"mock": "<name>", "scenario": "<name>" or null}')
    dev = _dev(request)
    dev.write_line(json.dumps({"mock": mock, "scenario": scenario}))
    return JsonResponse({"id": dev.id}, status_code=202)


def dev_routes() -> list[BaseRoute]:
    return [
        Route(DEVS, start_dev, methods=["POST"]),
        Route(DEVS, list_devs, methods=["GET"]),
        Route(DEV, dev_document, methods=["GET"]),
        Route(f"{DEV}/events", dev_events, methods=["GET"]),
        Route(f"{DEV}/stop", stop_dev, methods=["POST"]),
        Route(f"{DEV}/scenario", switch_scenario, methods=["POST"]),
    ]


def _checked_dev(environment: Environment, attempt_id: int) -> tuple[str, Path]:
    return check_dev(environment, attempt_id), environment.root


def _dev(request: Request) -> Child:
    return server_state(request).children.dev(request.path_params["dev_id"])


def _document(dev: Child) -> dict[str, JsonValue]:
    """`end` is the stream's `dev_end`, or null while the stack runs or when none came."""
    return {
        "id": dev.id,
        "attempt_id": dev.start.attempt_id,
        "state": RUNNING if dev.running else ENDED,
        "started_at": dev.started_at,
        "exit_code": dev.closed.exit_code if dev.closed else None,
        "end": dev.run_end,
    }
