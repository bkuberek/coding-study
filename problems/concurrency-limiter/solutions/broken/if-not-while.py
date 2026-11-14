import asyncio


class ConcurrencyLimiter:
    def __init__(self, limit: int) -> None:
        self._permits = limit
        self._waiters: list[asyncio.Future[None]] = []

    async def acquire(self) -> None:
        if self._permits == 0:
            waiter: asyncio.Future[None] = asyncio.get_running_loop().create_future()
            self._waiters.append(waiter)
            await waiter
        self._permits -= 1

    def try_acquire(self) -> bool:
        if self._permits == 0:
            return False
        self._permits -= 1
        return True

    def release(self) -> None:
        self._permits += 1
        waiters, self._waiters = self._waiters, []
        for waiter in waiters:
            if not waiter.done():
                waiter.set_result(None)

    def available(self) -> int:
        return self._permits
