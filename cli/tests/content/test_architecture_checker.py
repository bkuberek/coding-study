"""architecture-checker promises that its hidden cases catch the classic mistakes of checking an
import graph: an import resolved to the wrong module or at a name that is not a dot boundary, a
package read as one module, dependencies listed in the wrong order, a module counted as a cycle
of its own, a chain that is not the shortest or not the smallest, a layer rule read the wrong way
round or between neighbours only, an ignore or an exception that silences more than its import,
versions compared as text, and a ratchet that forgets what was fixed. These tests replay every
case against a model of the checker written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from itertools import permutations
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0339-architecture-checker"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

Edge = tuple[str, str]
Key = tuple[str, str, str]


class Contract:
    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self.pairs = pairs
        self.mode = "transitive"
        self.ignores: list[Edge] = []
        self.exceptions: dict[Edge, str] = {}


class Model:
    """The checker as the statement words it. Where the reference keeps one sorted adjacency list
    and walks it once per source, the model rebuilds the set of resolved imports for every
    question, computes distances in rounds with the smallest path to each module chosen
    explicitly, finds components by comparing reachable sets, and recomputes every pair of every
    contract on its own. Each mistake below overrides one rule or one method."""

    def __init__(self) -> None:
        self.modules: dict[str, list[str]] = {}
        self.contracts: dict[str, Contract] = {}
        self.version = "0"
        self.baseline: set[Key] = set()

    # --- names and the graph
    def inside(self, module: str, name: str) -> bool:
        return module == name or module.startswith(name + ".")

    def names_module(self, text: str, module: str) -> bool:
        return text == module or text.startswith(module + ".")

    def resolve(self, text: str) -> str | None:
        found = [module for module in self.modules if self.names_module(text, module)]
        return self.pick(found)

    def pick(self, found: list[str]) -> str | None:
        return max(found, key=len) if found else None

    def keeps(self, importer: str, imported: str) -> bool:
        return importer != imported

    def edges(self) -> set[Edge]:
        found = set()
        for module, imports in self.modules.items():
            for text in imports:
                target = self.resolve(text)
                if target is not None and self.keeps(module, target):
                    found.add((module, target))
        return found

    def members(self, name: str) -> set[str]:
        return {module for module in self.modules if self.inside(module, name)}

    def walk(self, starts: Iterable[str], edges: set[Edge]):
        """Distances in rounds, and for each module the smallest of its shortest paths."""
        best = {start: [start] for start in starts}
        distance = dict.fromkeys(best, 0)
        rounds = 0
        while True:
            rounds += 1
            reached: dict[str, list[str]] = {}
            for importer, imported in edges:
                if distance.get(importer) == rounds - 1 and imported not in distance:
                    path = [*best[importer], imported]
                    if imported not in reached or path < reached[imported]:
                        reached[imported] = path
            if not reached:
                return distance, best
            for module, path in reached.items():
                distance[module] = rounds
                best[module] = path

    # --- level 1
    def add_module(self, name: str, imports: list[str]) -> bool:
        is_new = name not in self.modules
        self.modules[name] = self.stored_imports(name, imports)
        return self.declared(is_new)

    def stored_imports(self, name: str, imports: list[str]) -> list[str]:
        return list(imports)

    def declared(self, is_new: bool) -> bool:
        return is_new

    def unknown_imports(self) -> list[list[str]]:
        rows = [
            [module, text]
            for module, imports in self.modules.items()
            for text in imports
            if self.resolve(text) is None
        ]
        return self.unknown_rows(rows)

    def unknown_rows(self, rows: list[list[str]]) -> list[list[str]]:
        return [list(row) for row in sorted({tuple(row) for row in rows})]

    def covered(self, name: str) -> set[str]:
        return self.members(name)

    def outside(self, module: str, name: str) -> bool:
        return not self.inside(module, name)

    def dependencies(self, name: str) -> list[str]:
        inner = self.covered(name)
        return sorted({b for a, b in self.edges() if a in inner and self.outside(b, name)})

    def transitive_dependencies(self, name: str) -> list[str]:
        distance, _ = self.walk(self.starts_of(name), self.edges())
        found = [module for module in distance if self.outside(module, name)]
        return self.nearest_first(found, distance)

    def starts_of(self, name: str) -> set[str]:
        return self.members(name)

    def nearest_first(self, found: list[str], distance: dict[str, int]) -> list[str]:
        return sorted(found, key=lambda module: (distance[module], module))

    # --- level 2
    def group(self, module: str, depth: int) -> str:
        return module if depth == 0 else ".".join(module.split(".")[:depth])

    def reachable(self, node: str, edges: set[Edge]) -> set[str]:
        seen: set[str] = set()
        todo = [node]
        while todo:
            current = todo.pop()
            for a, b in edges:
                if a == current and b not in seen:
                    seen.add(b)
                    todo.append(b)
        return seen

    def cycles(self, depth: int) -> list[list[str]]:
        edges = {(self.group(a, depth), self.group(b, depth)) for a, b in self.edges()}
        edges = {(a, b) for a, b in edges if a != b}
        nodes = {self.group(module, depth) for module in self.modules}
        reach = {node: self.reachable(node, edges) for node in nodes}
        parts = {
            frozenset([node, *(other for other in reach[node] if node in reach[other])])
            for node in nodes
        }
        return self.order_components(
            [self.sort_part(part) for part in parts if self.is_cycle(part)]
        )

    def sort_part(self, part: Iterable[str]) -> list[str]:
        return sorted(part)

    def is_cycle(self, part: frozenset[str]) -> bool:
        return len(part) > 1

    def order_components(self, parts: list[list[str]]) -> list[list[str]]:
        return sorted(parts)

    def cycle_chain(self, name: str) -> list[str]:
        if name not in self.modules:
            return []
        edges = self.edges()
        distance, best = self.walk([name], edges)
        options = [[*best[a], name] for a, b in edges if b == name and a in distance]
        return self.shortest_cycle(name, edges, options)

    def shortest_cycle(self, name: str, edges: set[Edge], options: list[list[str]]) -> list[str]:
        return min(options, key=lambda chain: (len(chain), chain)) if options else []

    # --- level 3
    def add_contract(self, contract: str, pairs: list[tuple[str, str]]) -> bool:
        if contract in self.contracts:
            return False
        self.contracts[contract] = Contract(pairs)
        return True

    def layer_pairs(self, layers: list[str]) -> list[tuple[str, str]]:
        return [(layers[low], layers[high]) for low in range(len(layers)) for high in range(low)]

    def add_layers(self, contract: str, layers: list[str]) -> bool:
        return self.add_contract(contract, self.layer_pairs(layers))

    def add_forbidden(self, contract: str, source: str, target: str) -> bool:
        return self.add_contract(contract, self.forbidden_pairs(source, target))

    def forbidden_pairs(self, source: str, target: str) -> list[tuple[str, str]]:
        return [(source, target)]

    def add_independence(self, contract: str, names: list[str]) -> bool:
        return self.add_contract(contract, self.independence_pairs(names))

    def independence_pairs(self, names: list[str]) -> list[tuple[str, str]]:
        return list(permutations(names, 2))

    def check(self) -> list[list[str]]:
        return [[*key, *chain] for key, chain in self.violations()]

    def violations(self) -> list[tuple[Key, list[str]]]:
        found = []
        for name, rules in self.contracts.items():
            kept = {edge for edge in self.edges() if not self.skipped(rules, edge)}
            for source, target in rules.pairs:
                chain = self.chain(rules, source, target, kept)
                if chain:
                    found.append(((name, source, target), chain))
        return self.order_rows(found)

    def order_rows(self, rows: list[tuple[Key, list[str]]]) -> list[tuple[Key, list[str]]]:
        return sorted(rows)

    def chain(
        self, rules: Contract, source: str, target: str, edges: set[Edge]
    ) -> list[str] | None:
        if self.is_direct(rules):
            return self.direct_chain(source, target, edges)
        return self.transitive_chain(source, target, edges)

    def is_direct(self, rules: Contract) -> bool:
        return rules.mode == "direct"

    def transitive_chain(self, source: str, target: str, edges: set[Edge]) -> list[str] | None:
        distance, best = self.walk(self.starts_of(source), edges)
        options = [best[module] for module in distance if self.inside(module, target)]
        return self.smallest_chain(options)

    def smallest_chain(self, options: list[list[str]]) -> list[str] | None:
        return min(options, key=lambda chain: (len(chain), chain)) if options else None

    def direct_chain(self, source: str, target: str, edges: set[Edge]) -> list[str] | None:
        options = [[a, b] for a, b in edges if self.inside(a, source) and self.inside(b, target)]
        return self.smallest_import(options)

    def smallest_import(self, options: list[list[str]]) -> list[str] | None:
        return min(options) if options else None

    # --- level 4
    def version_order(self, first: str, second: str) -> int:
        a = [int(part) for part in first.split(".")]
        b = [int(part) for part in second.split(".")]
        width = max(len(a), len(b))
        a += [0] * (width - len(a))
        b += [0] * (width - len(b))
        return (a > b) - (a < b)

    def live(self, until: str) -> bool:
        return self.version_order(self.version, until) < 0

    def rules_of(self, rules: Contract) -> list[Edge]:
        alive = [pair for pair, until in rules.exceptions.items() if self.live(until)]
        return [*rules.ignores, *alive]

    def skipped(self, rules: Contract, edge: Edge) -> bool:
        return any(self.covers(rule, edge) for rule in self.rules_of(rules))

    def covers(self, rule: Edge, edge: Edge) -> bool:
        return self.inside(edge[0], rule[0]) and self.inside(edge[1], rule[1])

    def ignore(self, contract: str, importer: str, imported: str) -> bool:
        rules = self.contracts.get(contract)
        if rules is None or (importer, imported) in rules.ignores:
            return False
        rules.ignores.append((importer, imported))
        return True

    def allow(self, contract: str, importer: str, imported: str, until: str) -> bool:
        rules = self.contracts.get(contract)
        if rules is None:
            return False
        old = rules.exceptions.get((importer, imported))
        if old is not None and self.same_version(old, until):
            return False
        rules.exceptions[(importer, imported)] = until
        return True

    def same_version(self, first: str, second: str) -> bool:
        return self.version_order(first, second) == 0

    def set_version(self, version: str) -> list[list[str]]:
        self.version = version
        return sorted(
            [name, pair[0], pair[1], until]
            for name, rules in self.contracts.items()
            for pair, until in rules.exceptions.items()
            if not self.live(until)
        )

    def set_mode(self, contract: str, mode: str) -> bool:
        rules = self.contracts.get(contract)
        if rules is None or rules.mode == mode:
            return False
        rules.mode = mode
        return True

    def set_baseline(self, entries: list[list[str]]) -> int:
        self.baseline = {(a, b, c) for a, b, c in entries}
        return len(self.baseline)

    def ratchet(self) -> list[list[str]]:
        current = dict(self.violations())
        new = sorted(key for key in current if key not in self.baseline)
        fixed = sorted(key for key in self.baseline if key not in current)
        self.forget(set(fixed))
        return [["new", *key, *current[key]] for key in new] + [["fixed", *key] for key in fixed]

    def forget(self, fixed: set[Key]) -> None:
        self.baseline -= fixed


# --- level 1 mistakes
class ResolvesToTheShortestPrefix(Model):
    """Resolves an import to the shortest declared module it starts with."""

    def pick(self, found: list[str]) -> str | None:
        return min(found, key=len) if found else None


class ResolvesWithoutADot(Model):
    """Lets an import start with a module name anywhere, so lib.coreutils names lib.core."""

    def names_module(self, text: str, module: str) -> bool:
        return text.startswith(module)


class ResolvesExactNamesOnly(Model):
    """Never reads an import as a name inside a module."""

    def names_module(self, text: str, module: str) -> bool:
        return text == module


class ResolvesWhenDeclared(Model):
    """Resolves the imports of a module once, against the modules declared up to then."""

    def __init__(self) -> None:
        super().__init__()
        self.known_then: dict[str, set[str]] = {}

    def add_module(self, name: str, imports: list[str]) -> bool:
        is_new = super().add_module(name, imports)
        self.known_then[name] = set(self.modules)
        return is_new

    def resolve_for(self, module: str, text: str) -> str | None:
        return self.pick([m for m in self.known_then[module] if self.names_module(text, m)])

    def edges(self) -> set[Edge]:
        return {
            (module, target)
            for module, imports in self.modules.items()
            for text in imports
            if (target := self.resolve_for(module, text)) is not None and module != target
        }

    def unknown_imports(self) -> list[list[str]]:
        return self.unknown_rows(
            [
                [module, text]
                for module, imports in self.modules.items()
                for text in imports
                if self.resolve_for(module, text) is None
            ]
        )


class PackageImportIsKnown(Model):
    """Takes an import of a package with no module of its own as known."""

    def unknown_imports(self) -> list[list[str]]:
        return [
            row
            for row in super().unknown_imports()
            if not any(module.startswith(row[1] + ".") for module in self.modules)
        ]


class InsideWithoutADot(Model):
    """Counts app.dbx as inside app.db."""

    def inside(self, module: str, name: str) -> bool:
        return module.startswith(name)


class RedeclaringMergesImports(Model):
    """Adds the new imports to the old ones."""

    def stored_imports(self, name: str, imports: list[str]) -> list[str]:
        return [*self.modules.get(name, []), *imports]


class RedeclaringReturnsTrue(Model):
    """Answers true when a module is declared again."""

    def declared(self, is_new: bool) -> bool:
        return True


class UnknownImportsRepeat(Model):
    """Lists an unknown import once per time it is written."""

    def unknown_rows(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows)


class DependenciesOfTheModuleOnly(Model):
    """Reads a name as one module, without the modules inside it."""

    def covered(self, name: str) -> set[str]:
        return {name} & set(self.modules)


class DependenciesKeepInternalImports(Model):
    """Lists the modules of a package that other modules of it import."""

    def dependencies(self, name: str) -> list[str]:
        inner = self.covered(name)
        return sorted({b for a, b in self.edges() if a in inner})


class TransitiveSortedByName(Model):
    """Sorts transitive dependencies by name only."""

    def nearest_first(self, found: list[str], distance: dict[str, int]) -> list[str]:
        return sorted(found)


class TransitiveListsModulesInside(Model):
    """Walks from each module of the package alone, and lists the other modules it reaches."""

    def transitive_dependencies(self, name: str) -> list[str]:
        edges = self.edges()
        rank: dict[str, int] = {}
        for start in self.members(name):
            distance, _ = self.walk([start], edges)
            for module, steps in distance.items():
                if module != start:
                    rank[module] = min(steps, rank.get(module, steps))
        return self.nearest_first(list(rank), rank)


class TransitiveCountsFromTheFirstModule(Model):
    """Measures distances from the first module of the package alone."""

    def transitive_dependencies(self, name: str) -> list[str]:
        members = sorted(self.members(name))
        if not members:
            return []
        distance, _ = self.walk(members[:1], self.edges())
        found = [module for module in distance if self.outside(module, name)]
        return self.nearest_first(found, distance)


# --- level 2 mistakes
class SingleModulesAreCycles(Model):
    """Reports every component, even a single module."""

    def is_cycle(self, part: frozenset[str]) -> bool:
        return True


class SelfImportIsACycle(Model):
    """Keeps an import of a name inside the module itself as an edge."""

    def keeps(self, importer: str, imported: str) -> bool:
        return True


class ComponentsLargestFirst(Model):
    """Orders the components by size."""

    def order_components(self, parts: list[list[str]]) -> list[list[str]]:
        return sorted(parts, key=lambda part: (-len(part), part))


class ComponentModulesUnsorted(Model):
    """Lists a component's modules in reverse order."""

    def sort_part(self, part: Iterable[str]) -> list[str]:
        return sorted(part, reverse=True)


class DepthIgnored(Model):
    """Finds cycles between modules whatever the depth."""

    def group(self, module: str, depth: int) -> str:
        return module


class DepthOffByOne(Model):
    """Groups by one part more than the depth."""

    def group(self, module: str, depth: int) -> str:
        return module if depth == 0 else ".".join(module.split(".")[: depth + 1])


class FirstCycleFoundDepthFirst(Model):
    """Returns the first cycle a depth-first search in name order meets."""

    def shortest_cycle(self, name: str, edges: set[Edge], options: list[list[str]]) -> list[str]:
        targets = {a: sorted(b for x, b in edges if x == a) for a, _ in edges}

        def search(path: list[str]) -> list[str] | None:
            for nxt in targets.get(path[-1], []):
                if nxt == name:
                    return [*path, name]
                if nxt not in path:
                    found = search([*path, nxt])
                    if found:
                        return found
            return None

        return search([name]) or []


class CycleBuiltBackwards(Model):
    """Builds the chain from the end, taking the smallest module one step closer each time."""

    def shortest_cycle(self, name: str, edges: set[Edge], options: list[list[str]]) -> list[str]:
        if not options:
            return []
        distance, _ = self.walk([name], edges)
        length = min(len(chain) for chain in options) - 1
        chain = [name]
        current = name
        for step in range(length - 1, -1, -1):
            current = min(a for a, b in edges if b == current and distance.get(a) == step)
            chain.append(current)
        return chain[::-1]


# --- level 3 mistakes
class LayersReadUpwards(Model):
    """Forbids a higher layer to import a lower one."""

    def layer_pairs(self, layers: list[str]) -> list[tuple[str, str]]:
        return [(layers[high], layers[low]) for low in range(len(layers)) for high in range(low)]


class NeighbouringLayersOnly(Model):
    """Checks each layer only against the layer right above it."""

    def layer_pairs(self, layers: list[str]) -> list[tuple[str, str]]:
        return [(layers[low], layers[low - 1]) for low in range(1, len(layers))]


class DirectImportsOnlyAtLevel3(Model):
    """Reads every contract as direct imports only."""

    def is_direct(self, rules: Contract) -> bool:
        return True


class ChainToTheSmallestTarget(Model):
    """Among the shortest chains, takes the one that ends at the smallest module."""

    def smallest_chain(self, options: list[list[str]]) -> list[str] | None:
        return min(options, key=lambda chain: (len(chain), chain[-1], chain)) if options else None


class ChainFromTheFirstSourceModule(Model):
    """Walks from the first module of the source and through the others."""

    def transitive_chain(self, source: str, target: str, edges: set[Edge]) -> list[str] | None:
        members = sorted(self.members(source))
        if not members:
            return None
        distance, best = self.walk(members[:1], edges)
        options = [best[module] for module in distance if self.inside(module, target)]
        return self.smallest_chain(options)


class IndependenceOneWay(Model):
    """Checks each pair of independent names in the listed order only."""

    def independence_pairs(self, names: list[str]) -> list[tuple[str, str]]:
        return [(a, b) for index, a in enumerate(names) for b in names[index + 1 :]]


class ForbiddenBothWays(Model):
    """Forbids the target to import the source as well."""

    def forbidden_pairs(self, source: str, target: str) -> list[tuple[str, str]]:
        return [(source, target), (target, source)]


class ContractNameReplaced(Model):
    """Replaces a contract whose name is taken."""

    def add_contract(self, contract: str, pairs: list[tuple[str, str]]) -> bool:
        self.contracts[contract] = Contract(pairs)
        return True


class RowsInDeclarationOrder(Model):
    """Lists the broken contracts in the order they were declared."""

    def order_rows(self, rows: list[tuple[Key, list[str]]]) -> list[tuple[Key, list[str]]]:
        names = list(self.contracts)
        return sorted(rows, key=lambda row: (names.index(row[0][0]), row))


# --- level 4 mistakes
class VersionsComparedAsText(Model):
    """Compares versions as text, so 1.10 comes before 1.9."""

    def version_order(self, first: str, second: str) -> int:
        return (first > second) - (first < second)


class MissingPartsAreSmaller(Model):
    """Puts 3 before 3.0."""

    def version_order(self, first: str, second: str) -> int:
        a = [int(part) for part in first.split(".")]
        b = [int(part) for part in second.split(".")]
        return (a > b) - (a < b)


class ExceptionLastsThroughItsVersion(Model):
    """Keeps an exception alive at the version it names."""

    def live(self, until: str) -> bool:
        return self.version_order(self.version, until) <= 0


class ExceptionsNeverExpire(Model):
    """Applies an exception at every version."""

    def live(self, until: str) -> bool:
        return True

    def set_version(self, version: str) -> list[list[str]]:
        self.version = version
        return sorted(
            [name, pair[0], pair[1], until]
            for name, rules in self.contracts.items()
            for pair, until in rules.exceptions.items()
            if self.version_order(version, until) >= 0
        )


class IgnoreForEveryContract(Model):
    """Applies an ignore to every contract."""

    def rules_of(self, rules: Contract) -> list[Edge]:
        everything = [pair for other in self.contracts.values() for pair in other.ignores]
        alive = [pair for pair, until in rules.exceptions.items() if self.live(until)]
        return [*everything, *alive]


class IgnoreExactModulesOnly(Model):
    """Matches an ignore against module names exactly."""

    def covers(self, rule: Edge, edge: Edge) -> bool:
        return rule == edge


class IgnoreDropsTheBreak(Model):
    """Drops a break when an ignored import is on its chain, instead of looking for another."""

    def violations(self) -> list[tuple[Key, list[str]]]:
        found = []
        for name, rules in self.contracts.items():
            for source, target in rules.pairs:
                chain = self.chain(rules, source, target, self.edges())
                steps = list(zip(chain or [], (chain or [])[1:], strict=False))
                if chain and not any(self.skipped(rules, step) for step in steps):
                    found.append(((name, source, target), chain))
        return self.order_rows(found)


class DirectModeIgnored(Model):
    """Stores the mode and keeps walking chains."""

    def is_direct(self, rules: Contract) -> bool:
        return False


class DirectPicksTheSmallestImported(Model):
    """Picks the direct import with the smallest imported module first."""

    def smallest_import(self, options: list[list[str]]) -> list[str] | None:
        return min(options, key=lambda pair: (pair[1], pair[0])) if options else None


class SetModeAlwaysTrue(Model):
    """Answers true when the mode does not change."""

    def set_mode(self, contract: str, mode: str) -> bool:
        if contract not in self.contracts:
            return False
        self.contracts[contract].mode = mode
        return True


class AllowEqualVersionChanges(Model):
    """Takes 1.10.0 as a new version for an exception until 1.10."""

    def same_version(self, first: str, second: str) -> bool:
        return first == second


class AllowKeepsTheFirstVersion(Model):
    """Refuses a new version for an import that has an exception."""

    def allow(self, contract: str, importer: str, imported: str, until: str) -> bool:
        rules = self.contracts.get(contract)
        if rules is None or (importer, imported) in rules.exceptions:
            return False
        rules.exceptions[(importer, imported)] = until
        return True


class SetVersionListsOnlyNewlyExpired(Model):
    """Lists only the exceptions that expire with this call."""

    def set_version(self, version: str) -> list[list[str]]:
        before = {tuple(row) for row in super().set_version(self.version)}
        return [row for row in super().set_version(version) if tuple(row) not in before]


class BaselineCountsRepeats(Model):
    """Counts every entry given, repeats included."""

    def set_baseline(self, entries: list[list[str]]) -> int:
        super().set_baseline(entries)
        return len(entries)


class BaselineAddsToTheOld(Model):
    """Adds the entries to the earlier baseline."""

    def set_baseline(self, entries: list[list[str]]) -> int:
        self.baseline |= {(a, b, c) for a, b, c in entries}
        return len(self.baseline)


class RatchetKeepsFixedEntries(Model):
    """Never drops an entry from the baseline."""

    def forget(self, fixed: set[Key]) -> None:
        pass


class RatchetAcceptsNewBreaks(Model):
    """Adds the new breaks to the baseline once reported."""

    def ratchet(self) -> list[list[str]]:
        rows = super().ratchet()
        self.baseline |= {(row[1], row[2], row[3]) for row in rows if row[0] == "new"}
        return rows


class RatchetFixedFirst(Model):
    """Lists the fixed entries before the new breaks."""

    def ratchet(self) -> list[list[str]]:
        rows = super().ratchet()
        return [row for row in rows if row[0] == "fixed"] + [row for row in rows if row[0] == "new"]


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, RecursionError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_reach_every_kind_of_ratchet_row_and_both_modes():
    kinds = {
        row[0]
        for case in HIDDEN_CASES
        for op, got in zip(case["ops"], case["expected"], strict=True)
        if op == "ratchet"
        for row in got
    }
    modes = {
        arguments[1]
        for case in HIDDEN_CASES
        for op, arguments in zip(case["ops"], case["args"], strict=True)
        if op == "setMode"
    }
    assert kinds == {"new", "fixed"}
    assert modes == {"direct", "transitive"}
