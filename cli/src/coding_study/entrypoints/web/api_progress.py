"""Progress (docs/specs/web-ui.md#mock-progress-and-health): `cstudy stats --json`; the
document `cstudy export` writes, as a download, writing nothing in the workspace; and
`cstudy import` of an uploaded export, after a confirmation."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.progress_backup import (
    EXPORT_FILE,
    export_progress,
    import_progress_document,
)
from coding_study.application.show_stats import StatsRequest, show_stats
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.progress_stats import StatsGrouping
from coding_study.entrypoints.commands.stats import parse_since, stats_document
from coding_study.entrypoints.web.bodies import object_body, switch
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.queries import choice
from coding_study.entrypoints.web.responses import JsonResponse

IMPORT_QUESTION = (
    "Import this file into progress.db? cstudy imports only into a database that holds no "
    "progress yet."
)
EXPORT_FIELD = "export"


async def stats(request: Request) -> Response:
    query = request.query_params
    grouping = choice(query, "by", StatsGrouping) or StatsGrouping.PATTERN
    stats_request = StatsRequest(grouping, parse_since(query.get("since")))
    return JsonResponse(await in_workspace(request, _stats, stats_request))


async def import_export(request: Request) -> Response:
    """Changes nothing without `confirm`, and answers the question instead."""
    body = await object_body(request)
    if EXPORT_FIELD not in body:
        raise UsageError(f"the request needs {EXPORT_FIELD}")
    if not switch(body, "confirm"):
        raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, IMPORT_QUESTION)
    row_counts = await in_workspace(request, import_progress_document, body[EXPORT_FIELD])
    return JsonResponse({"imported": dict(row_counts)})


async def export(request: Request) -> Response:
    text = await in_workspace(request, _export_text)
    disposition = f'attachment; filename="{EXPORT_FILE}"'
    return Response(
        text, media_type=JsonResponse.media_type, headers={"content-disposition": disposition}
    )


def progress_routes() -> list[BaseRoute]:
    return [
        Route("/api/v1/stats", stats, methods=["GET"]),
        Route("/api/v1/progress/export", export, methods=["GET"]),
        Route("/api/v1/progress/import", import_export, methods=["POST"]),
    ]


def _stats(environment: Environment, request: StatsRequest) -> dict[str, JsonValue]:
    return stats_document(show_stats(environment, request))


def _export_text(environment: Environment) -> str:
    return export_progress(environment).text
