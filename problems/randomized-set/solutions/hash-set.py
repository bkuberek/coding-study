import random
from itertools import islice


class RandomizedSet:
    def __init__(self) -> None:
        self.values: set[int] = set()

    def insert(self, value: int) -> bool:
        if value in self.values:
            return False
        self.values.add(value)
        return True

    def remove(self, value: int) -> bool:
        if value not in self.values:
            return False
        self.values.remove(value)
        return True

    def get_random(self) -> int:
        # A set has no positions: walk its iteration order to a random rank, O(n).
        rank = random.randrange(len(self.values))
        return next(islice(self.values, rank, None))
