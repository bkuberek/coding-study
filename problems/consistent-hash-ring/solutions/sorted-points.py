from bisect import bisect_left, insort

RING_SIZE = 1 << 32
FNV_OFFSET_BASIS = 2166136261
FNV_PRIME = 16777619


def fnv1a(text: str) -> int:
    """FNV-1a, 32 bits, over the UTF-8 bytes of the text."""
    value = FNV_OFFSET_BASIS
    for byte in text.encode("utf-8"):
        value = ((value ^ byte) * FNV_PRIME) % RING_SIZE
    return value


def labels_of(node: str, count: int) -> list[str]:
    """Point 0 is the bare name and point i is `i#node`: the number goes first, because FNV-1a
    mixes the first bytes of a text far better than its last ones."""
    return [node] + [f"{index}#{node}" for index in range(1, count)]


class HashRing:
    """The ring is a sorted list of points `(position, label, node)`: sorting by position and then
    by label is the ring order with its tie-break. A key's owner is the first point at or after
    the key's position, found by binary search, wrapping to the first point."""

    def __init__(self) -> None:
        self._points: list[tuple[int, str, str]] = []
        self._joined: list[str] = []
        self._counts: dict[str, int] = {}
        self._tracked: set[str] = set()
        self._report: list[list[str]] = []

    # Level 1
    def position_of(self, text: str) -> int:
        return fnv1a(text)

    def add_node(self, node: str) -> int:
        return fnv1a(node) if self.add_virtual_node(node, 1) else -1

    def remove_node(self, node: str) -> bool:
        if node not in self._joined:
            return False
        before = self._owners()
        self._points = [point for point in self._points if point[2] != node]
        self._joined.remove(node)
        del self._counts[node]
        self._report_moves(before)
        return True

    def nodes(self) -> list[str]:
        return sorted(self._joined)

    def node_for(self, key: str) -> str:
        return self._owner(self._points, fnv1a(key))

    def modulo_node_for(self, key: str) -> str:
        return self._modulo(self._joined, key)

    def count_moves(self, keys: list[str], node: str) -> list[int]:
        if node in self._joined:
            return []
        grown = sorted([*self._points, (fnv1a(node), node, node)])
        ring_moves = sum(
            self._owner(self._points, fnv1a(key)) != self._owner(grown, fnv1a(key)) for key in keys
        )
        joined = [*self._joined, node]
        modulo_moves = sum(self._modulo(self._joined, key) != self._modulo(joined, key) for key in keys)
        return [ring_moves, modulo_moves]

    # Level 2
    def add_virtual_node(self, node: str, count: int) -> bool:
        if node in self._joined or count < 1:
            return False
        before = self._owners()
        for label in labels_of(node, count):
            insort(self._points, (fnv1a(label), label, node))
        self._joined.append(node)
        self._counts[node] = count
        self._report_moves(before)
        return True

    def positions(self, node: str) -> list[int]:
        if node not in self._counts:
            return []
        return [fnv1a(label) for label in labels_of(node, self._counts[node])]

    def arc_share(self) -> list[int]:
        share = dict.fromkeys(self._joined, 0)
        for index, (position, _, node) in enumerate(self._points):
            previous = self._points[index - 1][0]
            share[node] += position - previous if index > 0 else position - previous + RING_SIZE
        return [share[node] for node in self.nodes()]

    def key_counts(self, keys: list[str]) -> list[int]:
        counts = dict.fromkeys(self._joined, 0)
        for key in keys:
            if self._points:
                counts[self.node_for(key)] += 1
        return [counts[node] for node in self.nodes()]

    # Level 3
    def track_keys(self, keys: list[str]) -> int:
        self._tracked.update(keys)
        return len(self._tracked)

    def last_moves(self) -> list[list[str]]:
        return [list(row) for row in self._report]

    def owned_keys(self, node: str) -> list[str]:
        return sorted(key for key in self._tracked if self.node_for(key) == node and node)

    # Level 4
    def replicas(self, key: str, count: int) -> list[str]:
        if count < 1 or not self._points:
            return []
        start = self._start(self._points, fnv1a(key))
        found: list[str] = []
        for step in range(len(self._points)):
            node = self._points[(start + step) % len(self._points)][2]
            if node not in found:
                found.append(node)
                if len(found) == count:
                    break
        return found

    def assign_bounded(self, keys: list[str], numerator: int, denominator: int) -> list[str]:
        if not self._points or not keys:
            return []
        nodes = len(self._joined)
        capacity = -(-(denominator + numerator) * len(keys) // (denominator * nodes))
        load = dict.fromkeys(self._joined, 0)
        assigned = []
        for key in keys:
            index = self._start(self._points, fnv1a(key))
            while load[self._points[index][2]] >= capacity:
                index = (index + 1) % len(self._points)
            node = self._points[index][2]
            load[node] += 1
            assigned.append(node)
        return assigned

    # Shared
    @staticmethod
    def _start(points: list[tuple[int, str, str]], position: int) -> int:
        index = bisect_left(points, (position, ""))
        return index if index < len(points) else 0

    @classmethod
    def _owner(cls, points: list[tuple[int, str, str]], position: int) -> str:
        return points[cls._start(points, position)][2] if points else ""

    @staticmethod
    def _modulo(joined: list[str], key: str) -> str:
        return joined[fnv1a(key) % len(joined)] if joined else ""

    def _owners(self) -> dict[str, str]:
        return {key: self.node_for(key) for key in self._tracked}

    def _report_moves(self, before: dict[str, str]) -> None:
        after = self._owners()
        self._report = [[key, before[key], after[key]] for key in sorted(before) if before[key] != after[key]]
