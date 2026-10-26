"""In-Memory Database. Statement: .statements/in-memory-db.md. Run: cstudy test in-memory-db"""


class InMemoryDb:
    def __init__(self) -> None:
        pass

    # Level 1
    def set(self, timestamp: int, key: str, field: str, value: str) -> None:
        raise NotImplementedError

    # Level 1
    def get(self, timestamp: int, key: str, field: str) -> str:
        raise NotImplementedError

    # Level 2
    def scan_by_prefix(self, timestamp: int, key: str, prefix: str) -> list[str]:
        raise NotImplementedError
