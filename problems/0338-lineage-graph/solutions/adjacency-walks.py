from collections import deque

USAGES = frozenset({"identity", "transform", "aggregate", "filter"})
MASKABLE = frozenset({"transform", "aggregate"})
NAME_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")


class _Edge:
    __slots__ = ("source", "target", "usage", "masking")

    def __init__(self, source: str, target: str, usage: str, masking: bool) -> None:
        self.source = source
        self.target = target
        self.usage = usage
        self.masking = masking

    def carries_value(self) -> bool:
        return self.usage != "filter" and not self.masking


def _is_name(text: str) -> bool:
    return 1 <= len(text) <= 20 and all(ch in NAME_CHARACTERS for ch in text)


def _is_column_ref(text: str) -> bool:
    parts = text.split(".")
    return len(parts) == 2 and all(_is_name(part) for part in parts)


class LineageGraph:
    """Columns are nodes named `dataset.column`, and each lineage edge points from an input column
    to the column computed from it. Two adjacency maps, forward and backward, answer every walk:
    a breadth-first search gives distances for the ordered queries, a filter on the edge's usage
    restricts a walk to the edges a change or a label travels along, and Kosaraju's two passes
    group the columns that sit on a cycle."""

    def __init__(self) -> None:
        self._columns: dict[str, list[str]] = {}
        self._edges: list[_Edge] = []
        self._forward: dict[str, list[_Edge]] = {}
        self._backward: dict[str, list[_Edge]] = {}
        self._labels: dict[str, set[str]] = {}
        self._published: set[str] = set()

    # Level 1
    def add_dataset(self, name: str, columns: list[str], edges: list[list[str]]) -> bool:
        if name in self._columns or not _is_name(name) or not all(map(_is_name, columns)):
            return False
        if len(set(columns)) != len(columns):
            return False
        pairs = set()
        parsed = []
        for edge in edges:
            if not 3 <= len(edge) <= 4 or edge[0] not in columns or not _is_column_ref(edge[1]):
                return False
            usage, masking = edge[2], len(edge) == 4
            if usage not in USAGES or masking and (edge[3] != "masking" or usage not in MASKABLE):
                return False
            if (edge[0], edge[1]) in pairs:
                return False
            pairs.add((edge[0], edge[1]))
            parsed.append(_Edge(edge[1], f"{name}.{edge[0]}", usage, masking))
        self._columns[name] = list(columns)
        for edge in parsed:
            self._edges.append(edge)
            self._forward.setdefault(edge.source, []).append(edge)
            self._backward.setdefault(edge.target, []).append(edge)
        return True

    def validate(self) -> list[list[str]]:
        issues = []
        for edge in self._edges:
            dataset, column = edge.source.split(".")
            if dataset not in self._columns:
                issues.append(["unknown-dataset", edge.target, edge.source])
            elif column not in self._columns[dataset]:
                issues.append(["unknown-column", edge.target, edge.source])
        issues.extend(["cycle", *group] for group in self._cycles())
        return sorted(issues)

    def inputs_of(self, column: str) -> list[str]:
        return sorted(edge.source for edge in self._backward.get(column, []))

    # Level 2
    def upstream(self, column: str) -> list[str]:
        return self._by_distance(self._walk(column, self._backward, lambda e: e.source))

    def downstream(self, column: str) -> list[str]:
        return self._by_distance(self._walk(column, self._forward, lambda e: e.target))

    # Level 3
    def impact(self, column: str, change: str) -> list[list[str]]:
        reached = self._affected(column, change)
        return [
            [name, "direct" if reached[name] == 1 else "derived"]
            for name in self._by_distance(reached)
        ]

    def is_breaking(self, column: str, change: str) -> bool:
        if change != "retype":
            return bool(self._affected(column, change))
        typed = self._walk_from(column, lambda e: e.usage == "identity", include_start=True)
        return any(e.usage != "identity" for name in typed for e in self._forward.get(name, []))

    def impacted_datasets(self, column: str, change: str) -> list[str]:
        return sorted({name.split(".")[0] for name in self._affected(column, change)})

    # Level 4
    def tag(self, column: str, label: str) -> bool:
        if not self._declared(column) or label in self._labels.get(column, set()):
            return False
        self._labels.setdefault(column, set()).add(label)
        return True

    def tags_of(self, column: str) -> list[str]:
        sources = self._walk(column, self._backward, lambda e: e.source, _Edge.carries_value)
        sources[column] = 0
        return sorted({label for name in sources for label in self._labels.get(name, set())})

    def publish(self, dataset: str) -> bool:
        if dataset not in self._columns or dataset in self._published:
            return False
        self._published.add(dataset)
        return True

    def exposures(self, label: str) -> list[list[str]]:
        found = []
        for source, labels in self._labels.items():
            if label not in labels:
                continue
            reached = self._walk_from(source, _Edge.carries_value, include_start=True)
            found.extend(
                [name, source] for name in reached if name.split(".")[0] in self._published
            )
        return sorted(found)

    # Helpers
    def _declared(self, column: str) -> bool:
        if not _is_column_ref(column):
            return False
        dataset, name = column.split(".")
        return name in self._columns.get(dataset, [])

    def _walk(self, start, adjacency, step, keep=lambda e: True) -> dict[str, int]:
        """Breadth-first distances from `start` along the kept edges; `start` itself is in the
        answer only when an edge leads back to it."""
        distance: dict[str, int] = {}
        queue = deque([(start, 0)])
        while queue:
            node, steps = queue.popleft()
            for edge in adjacency.get(node, []):
                nxt = step(edge)
                if keep(edge) and nxt not in distance:
                    distance[nxt] = steps + 1
                    queue.append((nxt, steps + 1))
        return distance

    def _walk_from(self, start: str, keep, include_start: bool) -> dict[str, int]:
        reached = self._walk(start, self._forward, lambda e: e.target, keep)
        if include_start:
            reached.setdefault(start, 0)
        return reached

    def _affected(self, column: str, change: str) -> dict[str, int]:
        if change == "drop":
            return self._walk(column, self._forward, lambda e: e.target)
        if change == "rename":
            return {edge.target: 1 for edge in self._forward.get(column, [])}
        typed = self._walk(column, self._forward, lambda e: e.target, lambda e: e.usage == "identity")
        typed[column] = 0
        affected: dict[str, int] = {}
        for name, steps in typed.items():
            for edge in self._forward.get(name, []):
                if edge.target not in affected or steps + 1 < affected[edge.target]:
                    affected[edge.target] = steps + 1
        return affected

    @staticmethod
    def _by_distance(distance: dict[str, int]) -> list[str]:
        return sorted(distance, key=lambda name: (distance[name], name))

    def _cycles(self) -> list[list[str]]:
        """Strongly connected groups that hold a cycle, by Kosaraju's two passes."""
        nodes = sorted({e.source for e in self._edges} | {e.target for e in self._edges})
        finished: list[str] = []
        seen: set[str] = set()
        for root in nodes:
            if root in seen:
                continue
            seen.add(root)
            stack = [(root, iter(self._forward.get(root, [])))]
            while stack:
                node, edges = stack[-1]
                edge = next(edges, None)
                if edge is None:
                    stack.pop()
                    finished.append(node)
                elif edge.target not in seen:
                    seen.add(edge.target)
                    stack.append((edge.target, iter(self._forward.get(edge.target, []))))
        group_of: dict[str, int] = {}
        groups: list[list[str]] = []
        for root in reversed(finished):
            if root in group_of:
                continue
            group_of[root] = len(groups)
            members, pending = [root], [root]
            while pending:
                node = pending.pop()
                for edge in self._backward.get(node, []):
                    if edge.source not in group_of:
                        group_of[edge.source] = len(groups)
                        members.append(edge.source)
                        pending.append(edge.source)
            groups.append(sorted(members))
        self_loops = {e.source for e in self._edges if e.source == e.target}
        return [g for g in groups if len(g) > 1 or g[0] in self_loops]
