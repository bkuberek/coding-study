"""`GET /api/v1/about` and `GET /api/v1/about/licenses`: the data of `cstudy about`, for the About
view (docs/specs/web-ui.md#about-view)."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.about import read_about, read_license_texts
from coding_study.domain.cases import JsonValue
from coding_study.entrypoints.installed_packages import InstalledSoftware
from coding_study.entrypoints.web.context import ServerSettings, server_state
from coding_study.entrypoints.web.documents import about_document
from coding_study.entrypoints.web.responses import JsonResponse


async def about(request: Request) -> Response:
    server = server_state(request)
    return JsonResponse(await server.worker.run(_about, server.settings))


async def licenses(request: Request) -> Response:
    server = server_state(request)
    return JsonResponse(await server.worker.run(_licenses, server.settings))


def about_routes() -> list[BaseRoute]:
    return [
        Route("/api/v1/about", about, methods=["GET"]),
        Route("/api/v1/about/licenses", licenses, methods=["GET"]),
    ]


def _about(settings: ServerSettings) -> dict[str, JsonValue]:
    packages = InstalledSoftware(settings.static_directory)
    return about_document(read_about(settings.version, packages))


def _licenses(settings: ServerSettings) -> dict[str, JsonValue]:
    return {"text": read_license_texts(InstalledSoftware(settings.static_directory))}
