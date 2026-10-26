import random


class RandomizedSet:
    def __init__(self) -> None:
        self.values: list[int] = []
        self.index_of: dict[int, int] = {}

    def insert(self, value: int) -> bool:
        if value in self.index_of:
            return False
        self.index_of[value] = len(self.values)
        self.values.append(value)
        return True

    def remove(self, value: int) -> bool:
        index = self.index_of.pop(value, None)
        if index is None:
            return False
        last = self.values.pop()
        if index < len(self.values):
            # Fill the gap with the former last value and record its new position.
            self.values[index] = last
            self.index_of[last] = index
        return True

    def get_random(self) -> int:
        return random.choice(self.values)
