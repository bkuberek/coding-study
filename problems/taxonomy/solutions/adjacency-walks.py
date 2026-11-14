class Taxonomy:
    """Every concept keeps the set of its parents and the set of its children. Questions about
    ancestors, descendants, cycles and expansion are breadth-first walks over those sets, so
    nothing recurses and a chain of 10^5 concepts is as safe as a flat list.

    Retired concepts keep their id and their labels, and a table of replacements sends them to a
    live concept; every method that takes an id first follows that table.
    """

    def __init__(self) -> None:
        self._label: dict[str, str] = {}
        self._up: dict[str, set[str]] = {}
        self._down: dict[str, set[str]] = {}
        self._alts: dict[str, list[str]] = {}
        self._index: dict[str, set[str]] = {}
        self._gone: dict[str, str] = {}
        self._same: dict[str, set[str]] = {}

    # Level 1
    def add_concept(self, concept: str, label: str, parents: list[str]) -> str:
        if concept in self._label:
            return "duplicate"
        if concept in parents:
            return "cycle"
        if any(parent not in self._label for parent in parents):
            return "unknown-broader"
        resolved = {self._follow(parent) for parent in parents}
        if any(self._scheme(parent) != self._scheme(concept) for parent in resolved):
            return "cross-scheme"
        self._label[concept] = label
        self._up[concept] = resolved
        self._down[concept] = set()
        self._alts[concept] = []
        self._same[concept] = set()
        for parent in resolved:
            self._down[parent].add(concept)
        self._index_label(concept, label)
        return "ok"

    def add_broader(self, narrower: str, broader: str) -> str:
        child, parent = self._follow(narrower), self._follow(broader)
        if child not in self._label or parent not in self._label:
            return "unknown-concept"
        if self._scheme(child) != self._scheme(parent):
            return "cross-scheme"
        if child == parent or child in self._reach(parent, self._up):
            return "cycle"
        self._up[child].add(parent)
        self._down[parent].add(child)
        return "ok"

    def pref_label(self, concept: str) -> str:
        concept = self._follow(concept)
        return self._label.get(concept, "")

    def broader(self, concept: str) -> list[str]:
        concept = self._follow(concept)
        return sorted(self._up.get(concept, ()))

    def narrower(self, concept: str) -> list[str]:
        concept = self._follow(concept)
        return sorted(self._down.get(concept, ()))

    def ancestors(self, concept: str) -> list[str]:
        return self._nearest_first(self._follow(concept), self._up)

    def descendants(self, concept: str) -> list[str]:
        return self._nearest_first(self._follow(concept), self._down)

    def roots(self) -> list[str]:
        return sorted(c for c in self._label if c not in self._gone and not self._up[c])

    # Level 2
    def lowest_common_ancestors(self, first: str, second: str) -> list[str]:
        first, second = self._follow(first), self._follow(second)
        if first not in self._label or second not in self._label:
            return []
        common = self._reach(first, self._up) & self._reach(second, self._up)
        return sorted(c for c in common if not any(kid in common for kid in self._down[c]))

    # Level 3
    def add_alt_label(self, concept: str, label: str) -> str:
        concept = self._follow(concept)
        if concept not in self._label:
            return "unknown-concept"
        key = self._normalize(label)
        if key == "":
            return "empty-label"
        if key in self._keys_of(concept):
            return "duplicate"
        self._alts[concept].append(label)
        self._index_label(concept, label)
        return "ok"

    def alt_labels(self, concept: str) -> list[str]:
        return list(self._alts.get(self._follow(concept), ()))

    def find_by_label(self, label: str) -> list[str]:
        return sorted(self._matching(label))

    def expand(self, labels: list[str]) -> list[str]:
        found: set[str] = set()
        for label in labels:
            found |= self._matching(label)
        seen = set(found)
        queue = list(found)
        for current in queue:
            for kid in self._down[current]:
                if kid not in seen:
                    seen.add(kid)
                    queue.append(kid)
        return sorted(seen)

    # Level 4
    def rename(self, concept: str, label: str) -> str:
        concept = self._follow(concept)
        if concept not in self._label:
            return "unknown-concept"
        old, key = self._label[concept], self._normalize(label)
        self._alts[concept] = [a for a in self._alts[concept] if self._normalize(a) != key]
        old_key = self._normalize(old)
        if old_key not in ("", key):
            self._alts[concept].append(old)
        self._label[concept] = label
        self._index_label(concept, label)
        return "ok"

    def remove_broader(self, narrower: str, broader: str) -> str:
        child, parent = self._follow(narrower), self._follow(broader)
        if child not in self._label or parent not in self._label:
            return "unknown-concept"
        if parent not in self._up[child]:
            return "no-link"
        self._up[child].remove(parent)
        self._down[parent].remove(child)
        return "ok"

    def deprecate(self, concept: str, replacement: str) -> str:
        if concept not in self._label or replacement not in self._label:
            return "unknown-concept"
        if concept in self._gone:
            return "deprecated"
        target = self._follow(replacement)
        if target == concept:
            return "same-concept"
        if self._scheme(target) != self._scheme(concept):
            return "cross-scheme"
        if self._down[concept]:
            return "has-narrower"
        for parent in self._up[concept]:
            self._down[parent].discard(concept)
        self._up[concept] = set()
        for partner in self._same[concept]:
            self._same[partner].discard(concept)
            self._same[partner].add(target)
            self._same[target].add(partner)
        self._same[concept] = set()
        self._gone[concept] = target
        return "ok"

    def resolve(self, concept: str) -> str:
        concept = self._follow(concept)
        return concept if concept in self._label else ""

    def add_exact_match(self, first: str, second: str) -> str:
        first, second = self._follow(first), self._follow(second)
        if first not in self._label or second not in self._label:
            return "unknown-concept"
        if self._scheme(first) == self._scheme(second):
            return "same-scheme"
        self._same[first].add(second)
        self._same[second].add(first)
        return "ok"

    def translate(self, concepts: list[str], scheme: str) -> list[str]:
        found: set[str] = set()
        for concept in self._known(concepts):
            found |= self._targets(concept, scheme)
        return sorted(found)

    def unmapped(self, concepts: list[str], scheme: str) -> list[str]:
        return sorted(c for c in self._known(concepts) if not self._targets(c, scheme))

    # Helpers
    @staticmethod
    def _scheme(concept: str) -> str:
        return concept.partition(":")[0] if ":" in concept else ""

    @staticmethod
    def _normalize(label: str) -> str:
        """Trim the spaces at both ends, turn each run of spaces into one, lower-case A to Z."""
        return " ".join(part for part in label.split(" ") if part).lower()

    def _follow(self, concept: str) -> str:
        start = concept
        while concept in self._gone:
            concept = self._gone[concept]
        if start != concept:
            self._gone[start] = concept
        return concept

    def _known(self, concepts: list[str]) -> list[str]:
        resolved = {self._follow(c) for c in concepts}
        return sorted(c for c in resolved if c in self._label)

    def _targets(self, concept: str, scheme: str) -> set[str]:
        if self._scheme(concept) == scheme:
            return {concept}
        return {p for p in self._same[concept] if self._scheme(p) == scheme}

    def _keys_of(self, concept: str) -> set[str]:
        return {self._normalize(t) for t in [self._label[concept], *self._alts[concept]]}

    def _index_label(self, concept: str, label: str) -> None:
        key = self._normalize(label)
        if key:
            self._index.setdefault(key, set()).add(concept)

    def _matching(self, label: str) -> set[str]:
        key = self._normalize(label)
        if not key:
            return set()
        return {self._follow(c) for c in self._index.get(key, ())}

    @staticmethod
    def _reach(start: str, edges: dict[str, set[str]]) -> set[str]:
        """The concept itself and everything above (or below) it."""
        seen = {start}
        queue = [start]
        for current in queue:
            for nxt in edges[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    @staticmethod
    def _nearest_first(start: str, edges: dict[str, set[str]]) -> list[str]:
        if start not in edges:
            return []
        seen = {start}
        level = [start]
        found: list[str] = []
        while level:
            following: set[str] = set()
            for current in level:
                following |= edges[current] - seen
            seen |= following
            level = sorted(following)
            found.extend(level)
        return found
