"""`/api/v1/guides` and `/api/v1/paths`: `cstudy learn` for the Guides view
(docs/specs/web-ui.md#guides). Each answers the `--json` document of the command it mirrors, built
by that command's own builder from the use case the command calls; a guide adds its HTML."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.learn import guide_page, learn_listing, mark_read, path_view
from coding_study.domain.cases import JsonValue
from coding_study.entrypoints.commands.learn import (
    guide_document,
    listing_document,
    marked_document,
    path_document,
)
from coding_study.entrypoints.web.bodies import object_body
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.markdown import render_guide_markdown
from coding_study.entrypoints.web.responses import JsonResponse

GUIDES = "/api/v1/guides"
ONE_GUIDE = f"{GUIDES}/{{slug}}"
ONE_PATH = "/api/v1/paths/{slug}"


def _slug(request: Request) -> str:
    return request.path_params["slug"]


async def list_guides(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _listing))


async def show_guide(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _guide, _slug(request)))


async def show_path(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _path, _slug(request)))


async def mark(request: Request) -> Response:
    """`cstudy learn <guide> --done`: the first time is kept, and marking again changes nothing."""
    await object_body(request)
    return JsonResponse(await in_workspace(request, _mark, _slug(request)))


def guide_routes() -> list[BaseRoute]:
    return [
        Route(GUIDES, list_guides, methods=["GET"]),
        Route(ONE_GUIDE, show_guide, methods=["GET"]),
        Route(f"{ONE_GUIDE}/read", mark, methods=["POST"]),
        Route(ONE_PATH, show_path, methods=["GET"]),
    ]


def _listing(environment: Environment) -> dict[str, JsonValue]:
    return listing_document(learn_listing(environment))


def _guide(environment: Environment, slug: str) -> dict[str, JsonValue]:
    page = guide_page(environment, slug)
    return {**guide_document(page), "html": render_guide_markdown(page.markdown)}


def _path(environment: Environment, slug: str) -> dict[str, JsonValue]:
    return path_document(path_view(environment, slug))


def _mark(environment: Environment, slug: str) -> dict[str, JsonValue]:
    return marked_document(mark_read(environment, slug))
