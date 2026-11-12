from collections import deque


def inside(module: str, name: str) -> bool:
    return module == name or module.startswith(name + ".")


def version_key(text: str) -> tuple[int, ...]:
    parts = [int(part) for part in text.split(".")]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


class Contract:
    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self.pairs = pairs
        self.direct = False
        self.ignores: set[tuple[str, str]] = set()
        self.exceptions: dict[tuple[str, str], str] = {}


class ArchitectureChecker:
    """Modules keep the imports as written. The first question after a change resolves every
    import to the longest declared module that is the import or a dotted prefix of it, and keeps
    one sorted list of targets per module, so every walk visits neighbours in name order.

    A breadth-first walk from a sorted list of starts, over sorted neighbours, reaches each module
    first along the shortest chain that is smallest in name order, so one walk per source name
    answers every pair of a contract that starts there. Cycles are the strongly connected
    components, found with two depth-first passes over the graph and its reverse.
    """

    def __init__(self) -> None:
        self._imports: dict[str, list[str]] = {}
        self._graph: dict[str, list[str]] | None = None
        self._contracts: dict[str, Contract] = {}
        self._version: tuple[int, ...] = ()
        self._baseline: set[tuple[str, str, str]] = set()

    # Level 1
    def add_module(self, name: str, imports: list[str]) -> bool:
        is_new = name not in self._imports
        self._imports[name] = list(imports)
        self._graph = None
        return is_new

    def unknown_imports(self) -> list[list[str]]:
        rows = {
            (module, text)
            for module, imports in self._imports.items()
            for text in imports
            if self._resolve(text) is None
        }
        return [list(row) for row in sorted(rows)]

    def dependencies(self, name: str) -> list[str]:
        graph = self._edges()
        found = {
            target
            for module in self._members(name)
            for target in graph[module]
            if not inside(target, name)
        }
        return sorted(found)

    def transitive_dependencies(self, name: str) -> list[str]:
        order, parent = self._walk(self._members(name), None)
        depth: dict[str, int] = {}
        for module in order:
            above = parent[module]
            depth[module] = 0 if above is None else depth[above] + 1
        reached = [module for module in order if not inside(module, name)]
        return sorted(reached, key=lambda module: (depth[module], module))

    # Level 2
    def cycles(self, depth: int) -> list[list[str]]:
        adjacency: dict[str, set[str]] = {}
        for module, targets in self._edges().items():
            group = self._group(module, depth)
            adjacency.setdefault(group, set())
            for target in targets:
                other = self._group(target, depth)
                if other != group:
                    adjacency[group].add(other)
        components = [part for part in self._components(adjacency) if len(part) > 1]
        return sorted(sorted(part) for part in components)

    def cycle_chain(self, name: str) -> list[str]:
        if name not in self._imports:
            return []
        graph = self._edges()
        order, parent = self._walk([name], None)
        for module in order:
            if name in graph[module]:
                return [*self._chain(module, parent), name]
        return []

    # Level 3
    def add_layers(self, contract: str, layers: list[str]) -> bool:
        pairs = [(layers[low], layers[high]) for low in range(len(layers)) for high in range(low)]
        return self._add_contract(contract, pairs)

    def add_forbidden(self, contract: str, source: str, target: str) -> bool:
        return self._add_contract(contract, [(source, target)])

    def add_independence(self, contract: str, names: list[str]) -> bool:
        pairs = [(first, second) for first in names for second in names if first != second]
        return self._add_contract(contract, pairs)

    def check(self) -> list[list[str]]:
        return [[*key, *chain] for key, chain in self._violations()]

    # Level 4
    def ignore(self, contract: str, importer: str, imported: str) -> bool:
        rules = self._contracts.get(contract)
        if rules is None or (importer, imported) in rules.ignores:
            return False
        rules.ignores.add((importer, imported))
        return True

    def allow(self, contract: str, importer: str, imported: str, until: str) -> bool:
        rules = self._contracts.get(contract)
        if rules is None:
            return False
        old = rules.exceptions.get((importer, imported))
        if old is not None and version_key(old) == version_key(until):
            return False
        rules.exceptions[(importer, imported)] = until
        return True

    def set_version(self, version: str) -> list[list[str]]:
        self._version = version_key(version)
        rows = [
            [name, importer, imported, until]
            for name, rules in self._contracts.items()
            for (importer, imported), until in rules.exceptions.items()
            if version_key(until) <= self._version
        ]
        return sorted(rows)

    def set_mode(self, contract: str, mode: str) -> bool:
        rules = self._contracts.get(contract)
        if rules is None or rules.direct == (mode == "direct"):
            return False
        rules.direct = mode == "direct"
        return True

    def set_baseline(self, entries: list[list[str]]) -> int:
        self._baseline = {(entry[0], entry[1], entry[2]) for entry in entries}
        return len(self._baseline)

    def ratchet(self) -> list[list[str]]:
        current = dict(self._violations())
        new = [["new", *key, *chain] for key, chain in current.items() if key not in self._baseline]
        fixed = sorted(key for key in self._baseline if key not in current)
        self._baseline -= set(fixed)
        return sorted(new) + [["fixed", *key] for key in fixed]

    # Helpers
    def _resolve(self, text: str) -> str | None:
        while text not in self._imports:
            cut = text.rfind(".")
            if cut < 0:
                return None
            text = text[:cut]
        return text

    def _edges(self) -> dict[str, list[str]]:
        if self._graph is None:
            graph = {}
            for module, imports in self._imports.items():
                targets = {self._resolve(text) for text in imports}
                targets.discard(None)
                targets.discard(module)
                graph[module] = sorted(targets)
            self._graph = graph
        return self._graph

    def _members(self, name: str) -> list[str]:
        return sorted(module for module in self._imports if inside(module, name))

    def _walk(self, starts: list[str], rules: Contract | None):
        """Breadth-first from the sorted starts over sorted neighbours: the discovery order, and
        for each module the module it was first reached from."""
        graph = self._edges()
        parent: dict[str, str | None] = {start: None for start in starts}
        order = list(starts)
        queue = deque(starts)
        while queue:
            module = queue.popleft()
            for target in graph[module]:
                if target not in parent and not self._skipped(rules, module, target):
                    parent[target] = module
                    order.append(target)
                    queue.append(target)
        return order, parent

    @staticmethod
    def _chain(module: str, parent: dict[str, str | None]) -> list[str]:
        chain = []
        step: str | None = module
        while step is not None:
            chain.append(step)
            step = parent[step]
        return chain[::-1]

    @staticmethod
    def _group(module: str, depth: int) -> str:
        return module if depth == 0 else ".".join(module.split(".")[:depth])

    @staticmethod
    def _components(adjacency: dict[str, set[str]]) -> list[list[str]]:
        nodes = sorted(adjacency)
        forward = {node: sorted(adjacency[node]) for node in nodes}
        reverse: dict[str, list[str]] = {node: [] for node in nodes}
        for node in nodes:
            for target in forward[node]:
                reverse[target].append(node)
        finished: list[str] = []
        seen: set[str] = set()
        for root in nodes:
            if root in seen:
                continue
            seen.add(root)
            stack = [(root, 0)]
            while stack:
                node, index = stack.pop()
                if index < len(forward[node]):
                    stack.append((node, index + 1))
                    target = forward[node][index]
                    if target not in seen:
                        seen.add(target)
                        stack.append((target, 0))
                else:
                    finished.append(node)
        assigned: set[str] = set()
        components = []
        for root in reversed(finished):
            if root in assigned:
                continue
            assigned.add(root)
            part, stack = [], [root]
            while stack:
                node = stack.pop()
                part.append(node)
                for source in reverse[node]:
                    if source not in assigned:
                        assigned.add(source)
                        stack.append(source)
            components.append(part)
        return components

    def _add_contract(self, contract: str, pairs: list[tuple[str, str]]) -> bool:
        if contract in self._contracts:
            return False
        self._contracts[contract] = Contract(pairs)
        return True

    def _skipped(self, rules: Contract | None, importer: str, imported: str) -> bool:
        if rules is None:
            return False
        live = [
            pair for pair, until in rules.exceptions.items() if self._version < version_key(until)
        ]
        return any(
            inside(importer, first) and inside(imported, second)
            for first, second in [*rules.ignores, *live]
        )

    def _violations(self) -> list[tuple[tuple[str, str, str], list[str]]]:
        found = []
        for name in sorted(self._contracts):
            rules = self._contracts[name]
            for source in sorted({first for first, _ in rules.pairs}):
                targets = [second for first, second in rules.pairs if first == source]
                for target, chain in self._chains(rules, source, targets):
                    found.append(((name, source, target), chain))
        return sorted(found)

    def _chains(self, rules: Contract, source: str, targets: list[str]):
        starts = self._members(source)
        if rules.direct:
            graph = self._edges()
            for target in targets:
                hits = [
                    [module, other]
                    for module in starts
                    for other in graph[module]
                    if inside(other, target) and not self._skipped(rules, module, other)
                ]
                if hits:
                    yield target, min(hits)
            return
        order, parent = self._walk(starts, rules)
        for target in targets:
            first = next((module for module in order if inside(module, target)), None)
            if first is not None:
                yield target, self._chain(first, parent)
