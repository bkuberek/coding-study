OPEN = 2**53 - 1
CURRENT = OPEN - 1
HUGE = 10**15


class TripleStore:
    """Every triple ever recorded gets a number and a list of spans, the periods during which it
    was present. Six hash indexes list the numbers by subject, predicate, object and the three
    pairs, and one more finds a whole triple, so any pattern with a bound position starts from a
    short list instead of a scan. Removing a triple only closes its span, so the history stays.

    A query joins its patterns one at a time, always taking the pattern whose candidate list is
    shortest under the variables bound so far, and a path is a breadth-first walk with a visited
    set, so a cycle ends the walk.
    """

    def __init__(self) -> None:
        self._triples: list[tuple[str, str, str]] = []
        self._spans: list[list[list]] = []
        self._exact: dict[tuple[str, str, str], int] = {}
        self._by: dict[str, dict] = {name: {} for name in ("s", "p", "o", "sp", "po", "so")}
        self._now = 0
        self._live = 0

    # Level 1
    def add(self, subject: str, predicate: str, obj: str) -> bool:
        return self.record(subject, predicate, obj, "", self._now)

    def remove(self, subject: str, predicate: str, obj: str) -> bool:
        return self.retract(subject, predicate, obj, self._now)

    def size(self) -> int:
        return self._live

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        wanted = [None if t == "?" else t for t in (subject, predicate, obj)]
        found = [self._triples[i] for i in self._candidates(*wanted) if self._present(i, CURRENT)]
        return [list(triple) for triple in sorted(found)]

    # Level 2 and 3
    def query(self, patterns: list[list[str]], columns: list[str]) -> list[list[str]]:
        return self._rows(patterns, columns, CURRENT, False)[0]

    # Level 4
    def record(self, subject: str, predicate: str, obj: str, source: str, time: int) -> bool:
        self._now = time
        triple = (subject, predicate, obj)
        number = self._exact.get(triple)
        if number is None:
            number = self._create(triple)
        spans = self._spans[number]
        if spans and spans[-1][1] == OPEN:
            if source and all(known != source for known, _ in spans[-1][2]):
                spans[-1][2].append((source, time))
            return False
        spans.append([time, OPEN, [(source, time)] if source else []])
        self._live += 1
        return True

    def retract(self, subject: str, predicate: str, obj: str, time: int) -> bool:
        self._now = time
        number = self._exact.get((subject, predicate, obj))
        if number is None or self._spans[number][-1][1] != OPEN:
            return False
        self._spans[number][-1][1] = time
        self._live -= 1
        return True

    def query_as_of(
        self, patterns: list[list[str]], columns: list[str], time: int
    ) -> list[list[str]]:
        return self._rows(patterns, columns, time, False)[0]

    def sources_as_of(
        self, patterns: list[list[str]], columns: list[str], time: int
    ) -> list[list[str]]:
        return self._rows(patterns, columns, time, True)[1]

    # Storage
    def _create(self, triple: tuple[str, str, str]) -> int:
        number = len(self._triples)
        self._triples.append(triple)
        self._spans.append([])
        self._exact[triple] = number
        subject, predicate, obj = triple
        keys = {
            "s": subject,
            "p": predicate,
            "o": obj,
            "sp": (subject, predicate),
            "po": (predicate, obj),
            "so": (subject, obj),
        }
        for name, key in keys.items():
            self._by[name].setdefault(key, []).append(number)
        return number

    def _present(self, number: int, when: int) -> bool:
        span = self._span_at(number, when)
        return span is not None

    def _span_at(self, number: int, when: int) -> list | None:
        for span in reversed(self._spans[number]):
            if span[0] <= when:
                return span if when < span[1] else None
        return None

    def _candidates(self, s: str | None, p: str | None, o: str | None):
        """The numbers of the triples that can match, from the narrowest index that applies."""
        if s is not None and p is not None and o is not None:
            number = self._exact.get((s, p, o))
            return [] if number is None else [number]
        if s is not None and p is not None:
            return self._by["sp"].get((s, p), [])
        if p is not None and o is not None:
            return self._by["po"].get((p, o), [])
        if s is not None and o is not None:
            return self._by["so"].get((s, o), [])
        if s is not None:
            return self._by["s"].get(s, [])
        if p is not None:
            return self._by["p"].get(p, [])
        if o is not None:
            return self._by["o"].get(o, [])
        return range(len(self._triples))

    # Queries
    def _rows(self, patterns, columns, when, track):
        found: list[tuple[tuple[str, ...], tuple[int, ...]]] = []
        self._search([tuple(p) for p in patterns], {}, [], columns, when, track, found)
        rows = sorted({row for row, _ in found})
        if not track:
            return [list(row) for row in rows], []
        sources: dict[tuple[str, ...], set[str]] = {row: set() for row in rows}
        for row, used in found:
            for number in used:
                span = self._span_at(number, when)
                if span is not None:
                    sources[row].update(name for name, at in span[2] if at <= when)
        return [list(row) for row in rows], [sorted(sources[row]) for row in rows]

    def _search(self, remaining, bindings, used, columns, when, track, found) -> None:
        if not remaining:
            found.append((tuple(bindings[name] for name in columns), tuple(used) if track else ()))
            return
        best = min(range(len(remaining)), key=lambda i: self._cost(remaining[i], bindings))
        pattern = remaining[best]
        rest = remaining[:best] + remaining[best + 1 :]
        for ends, number in self._matches(pattern, bindings, when):
            undo: list[str] = []
            if self._unify(pattern, ends, bindings, undo):
                if number is not None:
                    used.append(number)
                self._search(rest, bindings, used, columns, when, track, found)
                if number is not None:
                    used.pop()
            for name in undo:
                del bindings[name]

    @staticmethod
    def _value(token: str, bindings: dict[str, str]) -> str | None:
        if token == "?":
            return None
        if token.startswith("?"):
            return bindings.get(token)
        return token

    @staticmethod
    def _unify(pattern, ends, bindings, undo) -> bool:
        tokens = (
            (pattern[0], pattern[1], pattern[2]) if len(ends) == 3 else (pattern[0], pattern[2])
        )
        for token, value in zip(tokens, ends, strict=True):
            if token == "?":
                continue
            if not token.startswith("?"):
                if token != value:
                    return False
            elif token in bindings:
                if bindings[token] != value:
                    return False
            else:
                bindings[token] = value
                undo.append(token)
        return True

    def _cost(self, pattern, bindings) -> int:
        s, p, o = (self._value(t, bindings) for t in pattern)
        if pattern[1].endswith("+"):
            if s is None and o is None:
                return HUGE
            return len(self._by["p"].get(pattern[1][:-1], []))
        return len(self._candidates(s, p, o))

    def _matches(self, pattern, bindings, when):
        s, p, o = (self._value(t, bindings) for t in pattern)
        if pattern[1].endswith("+"):
            return [(pair, None) for pair in self._path_pairs(s, pattern[1][:-1], o, when)]
        return [(self._triples[n], n) for n in self._candidates(s, p, o) if self._present(n, when)]

    def _path_pairs(self, s, p, o, when):
        if s is not None:
            reached = self._reach(s, p, True, when)
            if o is not None:
                return [(s, o)] if o in reached else []
            return [(s, node) for node in reached]
        if o is not None:
            return [(node, o) for node in self._reach(o, p, False, when)]
        starts = {self._triples[n][0] for n in self._by["p"].get(p, []) if self._present(n, when)}
        return [(start, node) for start in starts for node in self._reach(start, p, True, when)]

    def _reach(self, start: str, p: str, forward: bool, when: int) -> set[str]:
        """The nodes at the end of one or more hops; the start is in it only through a cycle."""
        seen: set[str] = set()
        queue = [start]
        for node in queue:
            key = (node, p) if forward else (p, node)
            for number in self._by["sp" if forward else "po"].get(key, []):
                if self._present(number, when):
                    triple = self._triples[number]
                    following = triple[2] if forward else triple[0]
                    if following not in seen:
                        seen.add(following)
                        queue.append(following)
        return seen
