class MinStack:
    def __init__(self) -> None:
        # Each entry is (value, minimum of this value and everything below it).
        self.entries: list[tuple[int, int]] = []

    def push(self, value: int) -> None:
        minimum = min(value, self.entries[-1][1]) if self.entries else value
        self.entries.append((value, minimum))

    def pop(self) -> None:
        self.entries.pop()

    def top(self) -> int:
        return self.entries[-1][0]

    def get_min(self) -> int:
        return self.entries[-1][1]
