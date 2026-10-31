"""The one worker thread that runs use cases for the request handlers
(docs/specs/web-ui.md#process)."""

from collections.abc import Callable

from anyio import CapacityLimiter, to_thread


class UseCaseWorker:
    """Runs blocking calls one at a time, off the event loop, so use cases never run
    concurrently inside the server, as they never do within one `cstudy` command."""

    def __init__(self) -> None:
        self._limiter = CapacityLimiter(1)

    async def run[*Arguments, Result](
        self, function: Callable[[*Arguments], Result], *arguments: *Arguments
    ) -> Result:
        return await to_thread.run_sync(function, *arguments, limiter=self._limiter)
