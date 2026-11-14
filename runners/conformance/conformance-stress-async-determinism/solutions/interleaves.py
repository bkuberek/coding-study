import asyncio


class StressLog:
    def __init__(self) -> None:
        self._values: list[int] = []

    async def append(self, value: int) -> int:
        await asyncio.sleep(0)
        self._values.append(value)
        return len(self._values)
