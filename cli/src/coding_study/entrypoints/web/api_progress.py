"""`GET /api/v1/progress/export`: the document `cstudy export` writes, as a download, writing
nothing in the workspace (docs/specs/web-ui.md#mock-progress-and-health)."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.progress_backup import EXPORT_FILE, export_progress
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.responses import JsonResponse


async def export(request: Request) -> Response:
    text = await in_workspace(request, _export_text)
    disposition = f'attachment; filename="{EXPORT_FILE}"'
    return Response(
        text, media_type=JsonResponse.media_type, headers={"content-disposition": disposition}
    )


def progress_routes() -> list[BaseRoute]:
    return [Route("/api/v1/progress/export", export, methods=["GET"])]


def _export_text(environment: Environment) -> str:
    return export_progress(environment).text
