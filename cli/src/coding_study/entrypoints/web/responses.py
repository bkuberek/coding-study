"""JSON in and out of the API (docs/specs/web-ui.md#api-conventions)."""

import json

from starlette.requests import Request
from starlette.responses import JSONResponse

from coding_study.domain.errors import UsageError


class JsonResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


async def json_body(request: Request) -> object:
    """The request's JSON document; raises UsageError when the body is not JSON."""
    try:
        return json.loads(await request.body())
    except ValueError:
        raise UsageError("the request body is not JSON") from None
