"""Bounded Blocking Queue. Statement: .statements/bounded-blocking-queue.md. Run: cstudy test bounded-blocking-queue

Concurrency: threads
"""


class BoundedBlockingQueue:
    def __init__(self, capacity: int) -> None:
        pass

    def put(self, value: int) -> None:
        raise NotImplementedError

    def take(self) -> int:
        raise NotImplementedError

    def size(self) -> int:
        raise NotImplementedError
