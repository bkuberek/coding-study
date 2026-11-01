"""A stream opens at once (docs/specs/web-ui.md#server-sent-events): Firefox fires `open` on an
`EventSource` when the first bytes arrive, so a stream that has nothing to send yet sends a
comment line first, whatever stream it is."""

import asyncio
from collections.abc import AsyncIterator

from starlette.requests import Request

from coding_study.entrypoints.web.responses import OPENING, event_stream

TIMEOUT_S = 5.0


def request(headers: dict[str, str] | None = None) -> Request:
    pairs = (headers or {}).items()
    scope = {"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in pairs]}
    return Request(scope)


async def silent(_after: int | None) -> AsyncIterator[str]:
    """A stream with nothing to send, which stays open."""
    await asyncio.Event().wait()
    yield ""


async def one_frame(after: int | None) -> AsyncIterator[str]:
    yield f"id: {after}\n\n"


def test_a_stream_with_nothing_to_send_opens_with_a_comment_line():
    async def first_chunk() -> object:
        body = aiter(event_stream(request(), silent).body_iterator)
        return await asyncio.wait_for(anext(body), TIMEOUT_S)

    assert asyncio.run(first_chunk()) == OPENING


def test_the_opening_is_a_comment_an_event_source_ignores():
    assert OPENING.startswith(":")
    assert OPENING.endswith("\n\n")


def test_the_frames_follow_the_opening_and_the_last_event_id_still_reaches_them():
    async def chunks() -> list[object]:
        body = event_stream(request({"Last-Event-ID": "7"}), one_frame).body_iterator
        return [chunk async for chunk in body]

    assert asyncio.run(chunks()) == [OPENING, "id: 7\n\n"]
