import asyncio
from collections import deque


class ConcurrencyLimiter:
    def __init__(self, limit: int) -> None:
        self._permits = limit
        self._waiters: deque[asyncio.Future[None]] = deque()

    async def acquire(self) -> None:
        if self._permits > 0:
            self._permits -= 1
            return
        waiter: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._waiters.append(waiter)
        try:
            await waiter
        except asyncio.CancelledError:
            if not waiter.cancelled():
                self.release()
            raise

    def try_acquire(self) -> bool:
        if self._permits == 0:
            return False
        self._permits -= 1
        return True

    def release(self) -> None:
        while self._waiters:
            waiter = self._waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                return
        self._permits += 1

    def available(self) -> int:
        return self._permits
