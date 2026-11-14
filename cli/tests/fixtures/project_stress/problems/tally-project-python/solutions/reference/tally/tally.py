from tally.counts import Counts


class Tally:
    """Counts per key, which several threads may share from level 2."""

    def __init__(self) -> None:
        self._counts = Counts()

    def add(self, key: str, amount: int) -> int:
        return self._counts.add(key, amount)

    def count(self, key: str) -> int:
        return self._counts.get(key)

    def take(self, key: str, amount: int) -> bool:
        return self._counts.take(key, amount)
