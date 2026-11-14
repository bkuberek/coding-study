import random


class RandomizedSet:
    def __init__(self) -> None:
        self.values: list[int] = []

    def insert(self, value: int) -> bool:
        # `in` scans the list in C: O(n) per call.
        if value in self.values:
            return False
        self.values.append(value)
        return True

    def remove(self, value: int) -> bool:
        try:
            index = self.values.index(value)
        except ValueError:
            return False
        # Order does not matter: move the last value into the gap instead of shifting.
        self.values[index] = self.values[-1]
        self.values.pop()
        return True

    def get_random(self) -> int:
        return random.choice(self.values)
