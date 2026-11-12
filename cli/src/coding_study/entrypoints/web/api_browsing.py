"""Browsing: the problem list, one problem, its statement and history, and the next pick
(docs/specs/web-ui.md#browsing). Each answers the `--json` document of the command it mirrors,
built by that command's own builder from the use case the command calls."""

from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.learn import guide_entries
from coding_study.application.list_problems import ProblemFilter
from coding_study.application.next_problem import NextRequest, next_source, recommend
from coding_study.application.problem_details import problem_details
from coding_study.application.problem_history import problem_history
from coding_study.application.problem_sets import in_named_set
from coding_study.application.service_lifecycle import service_needs_of
from coding_study.application.show_statement import ShowRequest, show_statement
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UnknownProblemError
from coding_study.domain.items import EntryKind
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import ContentStatus, Difficulty, Language, Track
from coding_study.domain.scheduling import ProblemStatus
from coding_study.domain.taxonomy import Scope
from coding_study.entrypoints.commands.history import history_document
from coding_study.entrypoints.commands.list_problems import list_document
from coding_study.entrypoints.commands.next_problem import next_document
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.documents import markdown_document, problem_document
from coding_study.entrypoints.web.queries import choice, choice_list, positive_integer, switch
from coding_study.entrypoints.web.responses import JsonResponse

PROBLEMS = "/api/v1/problems"


async def problems(request: Request) -> Response:
    query = request.query_params
    problem_filter = ProblemFilter(
        track=choice(query, "track", Track),
        pattern=query.get("pattern"),
        difficulty=choice(query, "difficulty", Difficulty),
        status=choice(query, "status", ProblemStatus),
        content=choice(query, "content", ContentStatus),
        language=choice(query, "lang", Language),
        kind=choice(query, "kind", EntryKind),
        labels=_labels(query),
    )
    return JsonResponse(await in_workspace(request, _problems, problem_filter, _set_name(query)))


async def problem(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _problem, _slug(request)))


async def statement(request: Request) -> Response:
    show = ShowRequest(_slug(request), positive_integer(request.query_params, "level"))
    return JsonResponse(await in_workspace(request, _statement, show))


async def needs(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _needs, _slug(request)))


async def history(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _history, _slug(request)))


async def next_pick(request: Request) -> Response:
    query = request.query_params
    next_request = NextRequest(
        tracks=choice_list(query, "track", Track),
        pattern=query.get("pattern"),
        difficulty=choice(query, "difficulty", Difficulty),
        language=choice(query, "lang", Language),
        source=next_source(switch(query, "new"), switch(query, "review")),
        labels=_labels(query),
        set_name=_set_name(query),
    )
    return JsonResponse(await in_workspace(request, _next, next_request))


def browsing_routes() -> list[BaseRoute]:
    return [
        Route(PROBLEMS, problems, methods=["GET"]),
        Route(f"{PROBLEMS}/{{slug}}", problem, methods=["GET"]),
        Route(f"{PROBLEMS}/{{slug}}/statement", statement, methods=["GET"]),
        Route(f"{PROBLEMS}/{{slug}}/history", history, methods=["GET"]),
        Route(f"{PROBLEMS}/{{slug}}/needs", needs, methods=["GET"]),
        Route("/api/v1/next", next_pick, methods=["GET"]),
    ]


def _labels(query: QueryParams) -> LabelFilter:
    return LabelFilter(query.get("domain"), query.get("role"), choice(query, "scope", Scope))


def _set_name(query: QueryParams) -> str | None:
    return query.get("set") or None


def _problems(
    environment: Environment, problem_filter: ProblemFilter, set_name: str | None
) -> dict[str, JsonValue]:
    return list_document(environment, in_named_set(environment, problem_filter, set_name))


def _slug(request: Request) -> str:
    return request.path_params["slug"]


def _problem(environment: Environment, slug: str) -> dict[str, JsonValue]:
    details = problem_details(environment, slug)
    guides = guide_entries(environment, details.guides)
    return problem_document(_list_entry(environment, slug), details, guides)


def _list_entry(environment: Environment, slug: str) -> dict[str, JsonValue]:
    entries = list_document(environment, ProblemFilter())["entries"]
    assert isinstance(entries, list)
    for entry in entries:
        if isinstance(entry, dict) and entry.get("slug") == slug:
            return entry
    raise UnknownProblemError(slug)


def _statement(environment: Environment, show: ShowRequest) -> dict[str, JsonValue]:
    return markdown_document(show_statement(environment, show))


def _needs(environment: Environment, slug: str) -> dict[str, JsonValue]:
    """What `cstudy show` lists above the statement, each row with its state on this machine:
    asking starts nothing. Null for a problem that is not a service project."""
    rows = service_needs_of(environment, slug)
    return {
        "needs": None
        if rows is None
        else [{"label": row.label, "text": row.text, "problem": row.problem} for row in rows]
    }


def _history(environment: Environment, slug: str) -> dict[str, JsonValue]:
    return history_document(problem_history(environment, slug))


def _next(environment: Environment, request: NextRequest) -> dict[str, JsonValue]:
    return next_document(recommend(environment, request))
