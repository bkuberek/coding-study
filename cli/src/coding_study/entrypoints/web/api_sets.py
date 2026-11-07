"""`/api/v1/sets`: `cstudy set` for the Sets view and the add-to-set control
(docs/specs/web-ui.md#sets). Each write goes through the command's use case with the same refusals,
and answers the document of `cstudy set show --json`."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.problem_sets import (
    SetChange,
    add_to_set,
    create_set,
    delete_set,
    find_set,
    move_in_set,
    remove_from_set,
    rename_set,
)
from coding_study.domain.cases import JsonValue
from coding_study.entrypoints.commands.problem_sets import (
    delete_question,
    set_document,
    sets_document,
)
from coding_study.entrypoints.web.bodies import (
    object_body,
    optional_text,
    required_integer,
    required_text,
    required_text_list,
    switch,
)
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.responses import JsonResponse

SETS = "/api/v1/sets"
ONE_SET = f"{SETS}/{{name}}"
CREATED = 201


def _name(request: Request) -> str:
    return request.path_params["name"]


async def list_sets(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, sets_document))


async def show_set(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, set_document, _name(request)))


async def create(request: Request) -> Response:
    body = await object_body(request)
    name = required_text(body, "name")
    document = await in_workspace(request, _create, name, optional_text(body, "description"))
    return JsonResponse(document, status_code=CREATED)


async def add(request: Request) -> Response:
    slugs = required_text_list(await object_body(request), "slugs")
    return JsonResponse(await in_workspace(request, _add, _name(request), slugs))


async def remove(request: Request) -> Response:
    slugs = required_text_list(await object_body(request), "slugs")
    return JsonResponse(await in_workspace(request, _remove, _name(request), slugs))


async def move(request: Request) -> Response:
    body = await object_body(request)
    slug, position = required_text(body, "slug"), required_integer(body, "position")
    return JsonResponse(await in_workspace(request, _move, _name(request), slug, position))


async def rename(request: Request) -> Response:
    new_name = required_text(await object_body(request), "to")
    return JsonResponse(await in_workspace(request, _rename, _name(request), new_name))


async def delete(request: Request) -> Response:
    """Without `confirm` it changes nothing and answers the question `cstudy set delete` asks."""
    confirmed = switch(await object_body(request), "confirm")
    name = _name(request)
    if not confirmed:
        question = await in_workspace(request, _question, name)
        raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, question)
    await in_workspace(request, delete_set, name)
    return JsonResponse({"deleted": name})


def set_routes() -> list[BaseRoute]:
    return [
        Route(SETS, list_sets, methods=["GET"]),
        Route(SETS, create, methods=["POST"]),
        Route(ONE_SET, show_set, methods=["GET"]),
        Route(ONE_SET, delete, methods=["DELETE"]),
        Route(f"{ONE_SET}/add", add, methods=["POST"]),
        Route(f"{ONE_SET}/remove", remove, methods=["POST"]),
        Route(f"{ONE_SET}/move", move, methods=["POST"]),
        Route(f"{ONE_SET}/rename", rename, methods=["POST"]),
    ]


def _create(environment: Environment, name: str, description: str | None) -> dict[str, JsonValue]:
    create_set(environment, name, description)
    return set_document(environment, name)


def _add(environment: Environment, name: str, slugs: tuple[str, ...]) -> dict[str, JsonValue]:
    change = add_to_set(environment, name, slugs)
    return _change_document(environment, change, "added", "already")


def _remove(environment: Environment, name: str, slugs: tuple[str, ...]) -> dict[str, JsonValue]:
    change = remove_from_set(environment, name, slugs)
    return _change_document(environment, change, "removed", "absent")


def _change_document(
    environment: Environment, change: SetChange, changed: str, unchanged: str
) -> dict[str, JsonValue]:
    return {
        "set": set_document(environment, change.problem_set.name),
        changed: list(change.changed),
        unchanged: list(change.unchanged),
    }


def _move(environment: Environment, name: str, slug: str, position: int) -> dict[str, JsonValue]:
    move_in_set(environment, name, slug, position)
    return set_document(environment, name)


def _rename(environment: Environment, name: str, new_name: str) -> dict[str, JsonValue]:
    rename_set(environment, name, new_name)
    return set_document(environment, new_name)


def _question(environment: Environment, name: str) -> str:
    return delete_question(find_set(environment, name))
