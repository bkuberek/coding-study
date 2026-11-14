"""`/api/v1/docs`: `cstudy docs` for the Docs view (docs/specs/user-docs.md#docs-view). Each answers
the `--json` document of the command it mirrors, built by that command's own builder; the list adds
each page's passages for the view's search, and a page adds its HTML."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.user_docs import doc_page, docs_listing
from coding_study.domain.cases import JsonValue
from coding_study.domain.user_docs import DocPage
from coding_study.entrypoints.commands.docs import page_document, page_fields
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.markdown import render_doc_markdown
from coding_study.entrypoints.web.responses import JsonResponse

DOCS = "/api/v1/docs"
ONE_DOC = f"{DOCS}/{{slug}}"


async def list_docs(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _listing))


async def show_doc(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _page, request.path_params["slug"]))


def doc_routes() -> list[BaseRoute]:
    return [
        Route(DOCS, list_docs, methods=["GET"]),
        Route(ONE_DOC, show_doc, methods=["GET"]),
    ]


def _listing(environment: Environment) -> dict[str, JsonValue]:
    """`cstudy docs --json`, each page with its passages."""
    return {
        "pages": [
            {**page_fields(page), "passages": _passages(page)} for page in docs_listing(environment)
        ]
    }


def _page(environment: Environment, slug: str) -> dict[str, JsonValue]:
    page = doc_page(environment, slug)
    return {**page_document(page), "html": render_doc_markdown(page.markdown, page.slug)}


def _passages(page: DocPage) -> list[JsonValue]:
    return [
        {"id": passage.id, "title": passage.title, "text": passage.text}
        for passage in page.passages
    ]
