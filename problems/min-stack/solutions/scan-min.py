class MinStack:
    def __init__(self) -> None:
        self.values: list[int] = []

    def push(self, value: int) -> None:
        self.values.append(value)

    def pop(self) -> None:
        self.values.pop()

    def top(self) -> int:
        return self.values[-1]

    def get_min(self) -> int:
        # min() scans the whole list in C: O(n) per call.
        return min(self.values)
