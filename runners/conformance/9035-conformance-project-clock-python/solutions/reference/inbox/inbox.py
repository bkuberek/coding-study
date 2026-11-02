"""The entry class: `cstudy` imports `Inbox` from `inbox.inbox` and grades it on the virtual
clock.

`receive`, `sleep` and `race` wait on asyncio's clock, which the grader's event loop makes virtual.
`hold`, `jam`, `leave` and `strand` exist for the runner's conformance: `hold` waits on an event
nobody sets (a deadlock), `jam` blocks the event loop's thread on a lock it already holds (a wait
the clock cannot see), `leave` starts a task that never ends, and `strand` a thread that never ends.
"""

import asyncio
import threading

MILLISECONDS_PER_SECOND = 1000
RACE_DELAY_SECONDS = 0.01


class Inbox:
    def __init__(self) -> None:
        self._messages: asyncio.Queue[str] = asyncio.Queue()
        self._published = 0
        self._never = asyncio.Event()
        self._lock = threading.Lock()
        self._background: list[asyncio.Task[bool]] = []

    def publish(self, body: str) -> int:
        """Hands `body` to a waiting or later `receive`; returns how many messages were
        published."""
        self._messages.put_nowait(body)
        self._published += 1
        return self._published

    async def receive(self, wait_ms: int) -> str:
        """The next message, or "" once `wait_ms` milliseconds passed without one."""
        try:
            async with asyncio.timeout(wait_ms / MILLISECONDS_PER_SECOND):
                return await self._messages.get()
        except TimeoutError:
            return ""

    async def sleep(self, ms: int) -> int:
        """Waits `ms` milliseconds; returns how long it waited, as the loop's clock measures it."""
        loop = asyncio.get_running_loop()
        start = loop.time()
        await asyncio.sleep(ms / MILLISECONDS_PER_SECOND)
        return round((loop.time() - start) * MILLISECONDS_PER_SECOND)

    async def race(self, names: str) -> str:
        """One task per name, all waking at the same instant; the names in the order they woke,
        which the virtual clock's seed decides."""
        woke: list[str] = []

        async def wake(name: str) -> None:
            await asyncio.sleep(RACE_DELAY_SECONDS)
            woke.append(name)

        await asyncio.gather(*(wake(name) for name in names))
        return "".join(woke)

    async def hold(self) -> str:
        """Waits on an event nobody sets."""
        await self._never.wait()
        return ""

    def jam(self) -> str:
        """Takes a lock it already holds."""
        self._lock.acquire()
        self._lock.acquire()
        return ""

    def leave(self) -> None:
        """Starts a task that waits for good, and returns."""
        self._background.append(asyncio.get_running_loop().create_task(self._never.wait()))

    def strand(self) -> None:
        """Starts a thread that waits for good, and returns."""
        threading.Thread(target=threading.Event().wait, daemon=True).start()
