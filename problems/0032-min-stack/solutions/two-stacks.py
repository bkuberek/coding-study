class MinStack:
    def __init__(self) -> None:
        self.values: list[int] = []
        # The minimums in the order they took effect; the top is the current minimum.
        self.minimums: list[int] = []

    def push(self, value: int) -> None:
        self.values.append(value)
        # <= keeps one copy per equal minimum, so popping one copy keeps the others.
        if not self.minimums or value <= self.minimums[-1]:
            self.minimums.append(value)

    def pop(self) -> None:
        if self.values.pop() == self.minimums[-1]:
            self.minimums.pop()

    def top(self) -> int:
        return self.values[-1]

    def get_min(self) -> int:
        return self.minimums[-1]
