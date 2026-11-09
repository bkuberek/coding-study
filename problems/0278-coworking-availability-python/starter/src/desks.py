"""The hot desks the space holds itself: how many are left on each day it sells."""

import json
from pathlib import Path


class DeskInventory:
    def __init__(self, by_day: dict[str, int]) -> None:
        self._by_day = by_day

    @classmethod
    def from_file(cls, path: Path) -> "DeskInventory":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def available_on(self, day: str) -> int | None:
        """Desks left on `day`, written YYYY-MM-DD; None when it is not on sale."""
        return self._by_day.get(day)
