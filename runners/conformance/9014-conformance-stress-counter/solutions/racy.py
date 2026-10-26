class StressCounter:
    def __init__(self) -> None:
        self._count = 0

    def increment(self) -> int:
        count = self._count
        self._count = count + 1
        return count + 1
