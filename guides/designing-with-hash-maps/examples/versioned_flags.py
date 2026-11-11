"""Feature flags with history: each change is recorded at a release number, and a question asks
what a flag was set to in a given release.

A hash map finds the flag in O(1). Its history is a list of (release, value) appended in
increasing release order, so it is already sorted, and binary search finds the last change at or
before the release asked about in O(log h) for h changes.
"""

from bisect import bisect_right


class FlagHistory:
    def __init__(self) -> None:
        self.changes: dict[str, list[tuple[int, bool]]] = {}

    def set(self, flag: str, release: int, value: bool) -> None:
        history = self.changes.setdefault(flag, [])
        if history and release <= history[-1][0]:
            raise ValueError("releases must increase")
        history.append((release, value))

    def value_at(self, flag: str, release: int) -> bool | None:
        history = self.changes.get(flag, [])
        position = bisect_right(history, release, key=lambda change: change[0])
        return history[position - 1][1] if position > 0 else None


flags = FlagHistory()
flags.set("dark-mode", 1, False)
flags.set("dark-mode", 4, True)
flags.set("dark-mode", 9, False)
for release in (0, 1, 3, 4, 6, 9, 12):
    print(f"dark-mode in release {release:>2}:", flags.value_at("dark-mode", release))
print("an unknown flag:", flags.value_at("beta-search", 5))
