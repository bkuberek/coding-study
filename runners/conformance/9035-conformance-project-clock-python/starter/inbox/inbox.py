"""The entry class: `cstudy` imports `Inbox` from `inbox.inbox` and grades it on the virtual
clock."""


class Inbox:
    def publish(self, body: str) -> int:
        raise NotImplementedError

    async def receive(self, wait_ms: int) -> str:
        raise NotImplementedError

    async def sleep(self, ms: int) -> int:
        raise NotImplementedError

    async def race(self, names: str) -> str:
        raise NotImplementedError

    async def hold(self) -> str:
        raise NotImplementedError

    def jam(self) -> str:
        raise NotImplementedError

    def leave(self) -> None:
        raise NotImplementedError

    def strand(self) -> None:
        raise NotImplementedError
