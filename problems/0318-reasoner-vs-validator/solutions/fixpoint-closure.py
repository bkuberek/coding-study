from collections import defaultdict

TYPE = "rdf:type"
SUBCLASS = "rdfs:subClassOf"
DOMAIN = "rdfs:domain"
RANGE = "rdfs:range"
TRANSITIVE = "owl:TransitiveProperty"
INVERSE = "owl:inverseOf"
DISJOINT = "owl:disjointWith"
WILDCARD = "?"

ENTAILED = "entailed"
UNKNOWN = "unknown"
CONTRADICTED = "contradicted"
NO_ERROR = "no-error"
MIN_COUNT = "sh:MinCountConstraintComponent"
MAX_COUNT = "sh:MaxCountConstraintComponent"
CLASS = "sh:ClassConstraintComponent"
NO_LIMIT = -1

Triple = tuple[str, str, str]


class _Saturation:
    """Applies the rules of the statement to a set of triples until nothing new appears.

    Every rule has two premises, except the transitive rule, which has three (the declaration and
    two links). A new triple is joined with the triples that are already indexed, so the premise
    that arrives last finds the others.
    """

    def __init__(self) -> None:
        self.triples: set[Triple] = set()
        self.pairs: dict[str, set[tuple[str, str]]] = defaultdict(set)
        self.successors: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        self.predecessors: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        self.types_of_class: dict[str, set[str]] = defaultdict(set)
        self.domains: dict[str, set[str]] = defaultdict(set)
        self.ranges: dict[str, set[str]] = defaultdict(set)
        self.inverses: dict[str, set[str]] = defaultdict(set)
        self.transitive: set[str] = {SUBCLASS}
        self.superclasses: dict[str, set[str]] = defaultdict(set)
        self.pending: list[Triple] = []

    def run(self, asserted: set[Triple]) -> set[Triple]:
        self.pending = list(asserted)
        known: set[Triple] = set()
        while self.pending:
            triple = self.pending.pop()
            if triple in known:
                continue
            known.add(triple)
            self._index(triple)
            self._apply(triple)
        return known

    def _derive(self, subject: str, predicate: str, obj: str) -> None:
        self.pending.append((subject, predicate, obj))

    def _index(self, triple: Triple) -> None:
        subject, predicate, obj = triple
        self.pairs[predicate].add((subject, obj))
        self.successors[predicate][subject].add(obj)
        self.predecessors[predicate][obj].add(subject)
        if predicate == TYPE:
            self.types_of_class[obj].add(subject)
        elif predicate == DOMAIN:
            self.domains[subject].add(obj)
        elif predicate == RANGE:
            self.ranges[subject].add(obj)
        elif predicate == INVERSE:
            self.inverses[subject].add(obj)
            self.inverses[obj].add(subject)
        elif predicate == SUBCLASS:
            self.superclasses[subject].add(obj)
        if predicate == TYPE and obj == TRANSITIVE:
            self.transitive.add(subject)

    def _apply(self, triple: Triple) -> None:
        subject, predicate, obj = triple
        for cls in self.domains[predicate]:
            self._derive(subject, TYPE, cls)
        for cls in self.ranges[predicate]:
            self._derive(obj, TYPE, cls)
        for other in self.inverses[predicate]:
            self._derive(obj, other, subject)
        if predicate in self.transitive:
            for after in self.successors[predicate][obj]:
                self._derive(subject, predicate, after)
            for before in self.predecessors[predicate][subject]:
                self._derive(before, predicate, obj)
        if predicate == TYPE:
            for parent in self.superclasses[obj]:
                self._derive(subject, TYPE, parent)
        elif predicate == SUBCLASS:
            for member in self.types_of_class[subject]:
                self._derive(member, TYPE, obj)
        elif predicate == DOMAIN:
            for member, _ in self.pairs[subject]:
                self._derive(member, TYPE, obj)
        elif predicate == RANGE:
            for _, member in self.pairs[subject]:
                self._derive(member, TYPE, obj)
        elif predicate == INVERSE:
            for left, right in self.pairs[subject]:
                self._derive(right, obj, left)
            for left, right in self.pairs[obj]:
                self._derive(right, subject, left)
        if predicate == TYPE and obj == TRANSITIVE:
            for left, middle in self.pairs[subject]:
                for right in self.successors[subject][middle]:
                    self._derive(left, subject, right)


class _Property:
    def __init__(self, minimum: int, maximum: int, value_class: str) -> None:
        self.minimum = minimum
        self.maximum = maximum
        self.value_class = value_class


class KnowledgeBase:
    def __init__(self) -> None:
        self._asserted: set[Triple] = set()
        self._closure: set[Triple] | None = None
        self._shapes: dict[str, str] = {}
        self._properties: dict[str, dict[str, _Property]] = {}

    # Level 1
    def add(self, subject: str, predicate: str, obj: str) -> bool:
        triple = (subject, predicate, obj)
        if triple in self._asserted:
            return False
        self._asserted.add(triple)
        self._closure = None
        return True

    def closure(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        return [list(t) for t in sorted(self._matching(self._entailed(), subject, predicate, obj))]

    def types(self, resource: str) -> list[str]:
        return self._objects(self._entailed(), resource, TYPE)

    def instances(self, class_name: str) -> list[str]:
        return sorted({s for s, p, o in self._entailed() if p == TYPE and o == class_name})

    def super_classes(self, class_name: str) -> list[str]:
        return [c for c in self._objects(self._entailed(), class_name, SUBCLASS) if c != class_name]

    # Level 2
    def ask(self, subject: str, predicate: str, obj: str) -> str:
        entailed = self._entailed()
        if (subject, predicate, obj) in entailed:
            return ENTAILED
        if predicate == TYPE and self._would_clash(entailed, subject, obj):
            return CONTRADICTED
        return UNKNOWN

    # Level 3
    def inconsistencies(self) -> list[list[str]]:
        entailed = self._entailed()
        members: dict[str, set[str]] = defaultdict(set)
        for subject, predicate, obj in entailed:
            if predicate == TYPE:
                members[obj].add(subject)
        rows = set()
        for first, second in self._disjoint_pairs(entailed):
            for resource in members[first] & members[second]:
                rows.add((resource, first, second))
        return [list(row) for row in sorted(rows)]

    # Level 4
    def add_shape(self, shape: str, target_class: str) -> bool:
        if shape in self._shapes:
            return False
        self._shapes[shape] = target_class
        self._properties[shape] = {}
        return True

    def add_property(
        self, shape: str, path: str, min_count: int, max_count: int, value_class: str
    ) -> bool:
        if shape not in self._shapes or path in self._properties[shape]:
            return False
        self._properties[shape][path] = _Property(min_count, max_count, value_class)
        return True

    def validate(self) -> list[list[str]]:
        return [row[:5] for row in self._violations()]

    def contrast(self) -> list[list[str]]:
        entailed = self._entailed()
        rows = []
        for focus, shape, path, component, value in self._violations():
            if component == MAX_COUNT:
                answer = NO_ERROR
            elif component == MIN_COUNT:
                needed = self._properties[shape][path].minimum
                have = len(self._objects(entailed, focus, path))
                answer = ENTAILED if have >= needed else UNKNOWN
            else:
                answer = ENTAILED if (value, TYPE, self._properties[shape][path].value_class) in entailed else UNKNOWN
            rows.append([focus, shape, path, component, value, answer])
        return rows

    # Helpers
    def _entailed(self) -> set[Triple]:
        if self._closure is None:
            self._closure = _Saturation().run(self._asserted)
        return self._closure

    @staticmethod
    def _matching(triples: set[Triple], subject: str, predicate: str, obj: str) -> list[Triple]:
        return [
            t
            for t in triples
            if subject in (WILDCARD, t[0]) and predicate in (WILDCARD, t[1]) and obj in (WILDCARD, t[2])
        ]

    @staticmethod
    def _objects(triples: set[Triple], subject: str, predicate: str) -> list[str]:
        return sorted({o for s, p, o in triples if s == subject and p == predicate})

    @staticmethod
    def _disjoint_pairs(entailed: set[Triple]) -> set[tuple[str, str]]:
        return {(min(a, b), max(a, b)) for a, p, b in entailed if p == DISJOINT}

    def _would_clash(self, entailed: set[Triple], subject: str, cls: str) -> bool:
        held = set(self._objects(entailed, subject, TYPE))
        new = {cls, *self._objects(entailed, cls, SUBCLASS)}
        return any(
            (a in held and b in new) or (b in held and a in new)
            for a, b in self._disjoint_pairs(entailed)
        )

    def _violations(self) -> list[tuple[str, str, str, str, str]]:
        parents: dict[str, set[str]] = defaultdict(set)
        values: dict[tuple[str, str], set[str]] = defaultdict(set)
        direct: dict[str, set[str]] = defaultdict(set)
        for s, p, o in self._asserted:
            values[(s, p)].add(o)
            if p == SUBCLASS:
                parents[s].add(o)
            elif p == TYPE:
                direct[s].add(o)
        memo: dict[str, set[str]] = {}

        def shacl_types(node: str) -> set[str]:
            """The asserted types of a node and all their asserted superclasses."""
            if node not in memo:
                found = set(direct[node])
                stack = list(found)
                while stack:
                    for parent in parents[stack.pop()]:
                        if parent not in found:
                            found.add(parent)
                            stack.append(parent)
                memo[node] = found
            return memo[node]

        found_rows = set()
        for shape, target in self._shapes.items():
            for focus in [r for r in list(direct) if target in shacl_types(r)]:
                for path, rule in self._properties[shape].items():
                    nodes = values[(focus, path)]
                    if len(nodes) < rule.minimum:
                        found_rows.add((focus, shape, path, MIN_COUNT, ""))
                    if rule.maximum != NO_LIMIT and len(nodes) > rule.maximum:
                        found_rows.add((focus, shape, path, MAX_COUNT, ""))
                    if rule.value_class:
                        for node in nodes:
                            if rule.value_class not in shacl_types(node):
                                found_rows.add((focus, shape, path, CLASS, node))
        return sorted(found_rows)
