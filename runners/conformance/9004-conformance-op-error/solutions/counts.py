"""Conformance reference: increment counts up from 0; fail always raises."""


class Counter:
    def __init__(self) -> None:
        self.count = 0

    def increment(self) -> int:
        self.count += 1
        return self.count

    def fail(self) -> int:
        raise RuntimeError("counter failure")
