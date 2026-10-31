"""The entry class: `cstudy` imports `Inventory` from `store.inventory`.

It imports its sibling module both ways a project may, by package path and by relative path, and
both must reach the same module.
"""

from store import labels

from .labels import label_for

if labels.label_for is not label_for:
    raise ImportError("store.labels was loaded twice, under two module names")


class Inventory:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def add(self, name: str, count: int) -> int:
        self._counts[name] = self._counts.get(name, 0) + count
        return self._counts[name]

    def label(self, name: str) -> str:
        return label_for(name, self._counts.get(name, 0))
