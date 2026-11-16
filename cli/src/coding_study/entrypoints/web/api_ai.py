"""The AI preview's endpoints: status, usage, the keys and the consents
(docs/specs/web-ui.md#ai-preview). They run in-process and send nothing. A key arrives in the body
of a `PUT` and goes to `credentials.toml`; no response, error or log line holds it."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.ai_consent import parse_model, parse_purpose, revoke
from coding_study.application.ai_keys import parse_provider, remove_key, save_key
from coding_study.application.ai_status import ai_status
from coding_study.application.ai_usage import DEFAULT_DAYS, MAX_DAYS, MIN_DAYS, usage_report
from coding_study.application.environment import Environment
from coding_study.domain.ai import AiTask, ModelRef, Provider
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.commands.ai_report import status_document, usage_document
from coding_study.entrypoints.web.bodies import Body, object_body, required_text
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.responses import JsonResponse

DAYS = "days"
KEY = "key"


async def get_status(request: Request) -> Response:
    return JsonResponse(status_document(await in_workspace(request, ai_status)))


async def get_usage(request: Request) -> Response:
    report = await in_workspace(request, usage_report, _days(request))
    return JsonResponse(usage_document(report))


async def put_key(request: Request) -> Response:
    provider = _provider(request)
    text = _key_text(await object_body(request))
    await in_workspace(request, _save_key, provider, text)
    return JsonResponse({"provider": provider.value, "set": True})


async def delete_key(request: Request) -> Response:
    provider = _provider(request)
    await in_workspace(request, _remove_key, provider)
    return JsonResponse({"provider": provider.value, "set": False})


async def delete_consent(request: Request) -> Response:
    body = await object_body(request)
    provider = parse_provider(required_text(body, "provider"))
    model = parse_model(f"{provider}:{required_text(body, 'model')}")
    purpose = parse_purpose(required_text(body, "purpose"))
    revoked = await in_workspace(request, _revoke, model, purpose)
    return JsonResponse({"revoked": revoked})


def ai_routes() -> list[BaseRoute]:
    return [
        Route("/api/v1/ai/status", get_status, methods=["GET"]),
        Route("/api/v1/ai/usage", get_usage, methods=["GET"]),
        Route("/api/v1/ai/keys/{provider}", put_key, methods=["PUT"]),
        Route("/api/v1/ai/keys/{provider}", delete_key, methods=["DELETE"]),
        Route("/api/v1/ai/consents", delete_consent, methods=["DELETE"]),
    ]


def _save_key(environment: Environment, provider: Provider, text: str) -> None:
    save_key(environment.credentials, provider, text)


def _remove_key(environment: Environment, provider: Provider) -> None:
    remove_key(environment.credentials, provider)


def _revoke(environment: Environment, model: ModelRef, purpose: AiTask) -> bool:
    return revoke(environment, model, purpose)


def _provider(request: Request) -> Provider:
    """The provider the path names; an unknown one is a path that is not found."""
    try:
        return Provider(request.path_params["provider"])
    except ValueError:
        raise ApiError(ErrorCode.NOT_FOUND, f"not found: {request.url.path}") from None


def _key_text(body: Body) -> str:
    """The key of the body, never quoted in an error."""
    value = body.get(KEY)
    if value is None:
        raise UsageError(f"the request needs {KEY}")
    if not isinstance(value, str):
        raise UsageError(f"invalid {KEY}: use a string")
    return value


def _days(request: Request) -> int:
    value = request.query_params.get(DAYS)
    if value is None:
        return DEFAULT_DAYS
    if not value.isdecimal() or not MIN_DAYS <= int(value) <= MAX_DAYS:
        raise UsageError(f'invalid {DAYS} "{value}": use an integer from {MIN_DAYS} to {MAX_DAYS}')
    return int(value)
