"""`POST /api/v1/problems/{slug}/solution`: a reference solution, behind the question
`cstudy solution` asks before it grades an unsolved attempt `again`
(docs/specs/web-ui.md#solutions)."""

from dataclasses import dataclass

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.item_solution import reveal_item_solution
from coding_study.application.practice_catalog import is_item
from coding_study.application.reveal_solution import (
    SolutionRequest,
    attempt_to_mark,
    mark_revealed,
    show_solution,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.entrypoints.commands.solution import REVEAL_QUESTION
from coding_study.entrypoints.web.bodies import (
    Body,
    object_body,
    optional_choice,
    optional_text,
    switch,
)
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.responses import JsonResponse
from coding_study.entrypoints.web.solution_document import (
    item_solution_document,
    solution_document,
)

SOLUTION = "/api/v1/problems/{slug}/solution"
FIRST_BROKEN = ""
"""`--broken` without an id: the first broken reference with a file in the language."""


@dataclass(frozen=True, slots=True)
class Reveal:
    request: SolutionRequest
    confirmed: bool


async def solution(request: Request) -> Response:
    body = await object_body(request)
    selection = SolutionRequest(
        slug=request.path_params["slug"],
        language=optional_choice(body, "language", Language),
        approach_id=optional_text(body, "approach"),
        all_approaches=switch(body, "all"),
        explanation_only=switch(body, "explanation_only"),
        broken=_broken(body),
    )
    reveal = Reveal(selection, switch(body, "confirm"))
    return JsonResponse(await in_workspace(request, _reveal, reveal))


def solution_routes() -> list[BaseRoute]:
    return [Route(SOLUTION, solution, methods=["POST"])]


def _reveal(environment: Environment, reveal: Reveal) -> dict[str, JsonValue]:
    """As `cstudy solution`: the selection and the mock lock are checked before the question."""
    request = reveal.request
    if is_item(environment, request.slug):
        _require_item_options(request)
        return item_solution_document(reveal_item_solution(environment, request.slug))
    view = show_solution(environment, request)
    attempt = attempt_to_mark(environment, request.slug)
    if attempt is None:
        return solution_document(view, None)
    if not reveal.confirmed:
        raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, REVEAL_QUESTION)
    mark_revealed(environment, attempt)
    return solution_document(view, attempt.id)


def _broken(body: Body) -> str | None:
    """`true` for `--broken`, an id for `--broken=ID`, and null or false for neither."""
    value = body.get("broken")
    if value is None or value is False:
        return None
    if value is True:
        return FIRST_BROKEN
    if isinstance(value, str) and value:
        return value
    raise UsageError(f"invalid broken {value}: use true or a broken reference id")


def _require_item_options(request: SolutionRequest) -> None:
    """Items have one rubric and one reference: no languages and no approaches."""
    has_problem_options = (
        request.language is not None
        or request.approach_id is not None
        or request.all_approaches
        or request.explanation_only
        or request.broken is not None
    )
    if has_problem_options:
        raise UsageError(
            f"{request.slug} is not autograded; "
            "--lang, --approach, --all and --explanation-only apply to problems"
        )
