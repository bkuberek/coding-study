class Tally:
    """Counts per key."""

    def add(self, key: str, amount: int) -> int:
        raise NotImplementedError

    def count(self, key: str) -> int:
        raise NotImplementedError
