class OrgChart:
    """Rows are indexed once by id, then every question is a walk over the index.

    Nothing here recurses: the outline and the subtree sizes use an explicit stack and a
    breadth-first order, so a chain of 10^5 managers is as safe as a flat one.
    """

    def __init__(self) -> None:
        self._load([])

    # Level 1
    def load(self, rows: list[list[str]]) -> None:
        self._load(rows)

    def roots(self) -> list[str]:
        return list(self._children.get("", []))

    def name_of(self, employee: str) -> str:
        return self._names.get(employee, "")

    def children(self, employee: str) -> list[str]:
        return list(self._children.get(employee, [])) if employee in self._names else []

    # Level 2
    def orphans(self) -> list[str]:
        return list(self._orphans)

    def cycles(self) -> list[list[str]]:
        return [list(cycle) for cycle in self._cycles]

    # Level 3
    def chain(self, employee: str) -> list[str]:
        if employee not in self._depth:
            return []
        path = [employee]
        while self._parents[path[-1]] in self._names:
            path.append(self._parents[path[-1]])
        return path

    def lowest_common_manager(self, first: str, second: str) -> str:
        above_second = set(self.chain(second))
        for manager in self.chain(first):
            if manager in above_second:
                return manager
        return ""

    # Level 4
    def subtree_size(self, employee: str) -> int:
        return self._sizes.get(employee, 0)

    def outline(self, order: str) -> list[str]:
        lines: list[str] = []
        stack = [(top, 0) for top in reversed(self._sorted(self._tops, order))]
        while stack:
            current, depth = stack.pop()
            lines.append(f"{'  ' * depth}{self._names[current]} ({current})")
            kids = self._sorted(self._children.get(current, []), order)
            stack.extend((kid, depth + 1) for kid in reversed(kids))
        return lines

    def _sorted(self, ids: list[str], order: str) -> list[str]:
        if order == "name":
            return sorted(ids, key=lambda i: (self._names[i], i))
        if order == "size":
            return sorted(ids, key=lambda i: (-self._sizes[i], self._names[i], i))
        return ids

    def _load(self, rows: list[list[str]]) -> None:
        self._ids = [row[0] for row in rows]
        self._parents = {row[0]: row[1] for row in rows}
        self._names = {row[0]: row[2] for row in rows}
        self._children: dict[str, list[str]] = {}
        for row_id, parent, _ in rows:
            self._children.setdefault(parent, []).append(row_id)
        self._orphans = [
            i for i in self._ids if self._parents[i] != "" and self._parents[i] not in self._names
        ]
        orphan_set = set(self._orphans)
        self._tops = [i for i in self._ids if self._parents[i] == "" or i in orphan_set]
        self._depth: dict[str, int] = {}
        order = list(self._tops)
        for top in self._tops:
            self._depth[top] = 0
        for current in order:
            for kid in self._children.get(current, []):
                self._depth[kid] = self._depth[current] + 1
                order.append(kid)
        self._sizes = dict.fromkeys(order, 1)
        for current in reversed(order):
            parent = self._parents[current]
            if current in self._depth and parent in self._sizes and self._depth[current] > 0:
                self._sizes[parent] += self._sizes[current]
        self._cycles = self._find_cycles()

    def _find_cycles(self) -> list[list[str]]:
        position = {row_id: index for index, row_id in enumerate(self._ids)}
        seen: set[str] = set(self._depth)
        found: list[list[str]] = []
        for start in self._ids:
            walk: list[str] = []
            current = start
            while current not in seen:
                seen.add(current)
                walk.append(current)
                current = self._parents[current]
            if current in walk:
                cycle = walk[walk.index(current) :]
                first = min(range(len(cycle)), key=lambda k: position[cycle[k]])
                found.append(cycle[first:] + cycle[:first])
        found.sort(key=lambda cycle: position[cycle[0]])
        return found
