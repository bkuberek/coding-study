"""JSON in and out of the API (docs/specs/web-ui.md#api-conventions), and its streams of
server-sent events (docs/specs/web-ui.md#server-sent-events)."""

import json
from collections.abc import AsyncIterator, Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from coding_study.domain.errors import UsageError

EVENT_STREAM = "text/event-stream"
OPENING = ": open\n\n"
"""The first thing a stream sends: Firefox fires `open` on an `EventSource` when the first bytes
arrive, which would be the first notice or the keep-alive otherwise."""
LAST_EVENT_ID = "last-event-id"


class JsonResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


async def json_body(request: Request) -> object:
    """The request's JSON document; raises UsageError when the body is not JSON."""
    try:
        return json.loads(await request.body())
    except ValueError:
        raise UsageError("the request body is not JSON") from None


def event_stream(
    request: Request, frames: Callable[[int | None], AsyncIterator[str]]
) -> StreamingResponse:
    """The stream `frames` makes, after the message the request's `Last-Event-ID` names, which
    a stream that comes back sends; None for a new stream."""
    value = request.headers.get(LAST_EVENT_ID, "")
    after = int(value) if value.isdecimal() else None
    return StreamingResponse(_opened(frames(after)), media_type=EVENT_STREAM)


async def _opened(frames: AsyncIterator[str]) -> AsyncIterator[str]:
    yield OPENING
    async for frame in frames:
        yield frame
