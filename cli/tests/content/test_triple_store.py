"""triple-store promises that its hidden cases catch the classic mistakes of a small triple store:
duplicates counted, wildcards compared as text, joins that ignore a shared variable or a variable
that repeats inside one pattern, answers that are not distinct or not in the stated order, paths
that include the start of an acyclic walk or loop on a cycle, and histories that are lost when a
triple is removed or read with the wrong end of a span. These tests replay every case against a
model of the store written from the statement, which must give every expected output, and against
that model with one mistake planted at a time, which some hidden case must fail. A mistake that
crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0319-triple-store"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
FOREVER = float("inf")
CURRENT = 10**16
Triple = tuple[str, str, str]


class Model:
    """The store as the statement words it, one rule per method, so that each mistake below
    overrides a single method. It keeps the history of every triple as a list of spans and
    answers by looking at all of them, with no index."""

    def __init__(self) -> None:
        self.spans: dict[Triple, list[list[Any]]] = {}
        self.now = 0
        self.walked: dict[tuple[str, frozenset[tuple[str, str]]], set[tuple[str, str]]] = {}

    # --- what is present
    def present(self, triple: Triple, when: float) -> bool:
        return any(start <= when < end for start, end, _ in self.spans.get(triple, []))

    def span_at(self, triple: Triple, when: float) -> list[Any] | None:
        for span in self.spans.get(triple, []):
            if span[0] <= when < span[1]:
                return span
        return None

    def triples_at(self, when: float) -> list[Triple]:
        return [triple for triple in self.spans if self.present(triple, when)]

    # --- level 1
    def add(self, subject: str, predicate: str, obj: str) -> bool:
        return self.record(subject, predicate, obj, "", self.now)

    def remove(self, subject: str, predicate: str, obj: str) -> bool:
        return self.retract(subject, predicate, obj, self.now)

    def size(self) -> int:
        return len(self.triples_at(CURRENT))

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        wanted = (subject, predicate, obj)
        found = [
            triple
            for triple in self.triples_at(CURRENT)
            if all(w == "?" or w == t for w, t in zip(wanted, triple, strict=True))
        ]
        return [list(triple) for triple in sorted(found)]

    # --- level 2 and 3
    def is_variable(self, token: str) -> bool:
        return token.startswith("?") and token != "?"

    def unify(
        self, tokens: Sequence[str], values: Sequence[str], bindings: dict[str, str]
    ) -> dict[str, str] | None:
        merged = dict(bindings)
        for token, value in zip(tokens, values, strict=True):
            if token == "?":
                continue
            if self.is_variable(token):
                if merged.setdefault(token, value) != value:
                    return None
            elif token != value:
                return None
        return merged

    def edges(self, predicate: str, when: float) -> set[tuple[str, str]]:
        return {(s, o) for s, p, o in self.triples_at(when) if p == predicate}

    def closure(self, predicate: str, when: float) -> set[tuple[str, str]]:
        """Every pair joined by one or more hops of the predicate."""
        edges = self.edges(predicate, when)
        key = (predicate, frozenset(edges))
        if key not in self.walked:
            following: dict[str, set[str]] = {}
            for first, second in edges:
                following.setdefault(first, set()).add(second)
            pairs = set()
            for start in following:
                seen: set[str] = set()
                queue = [start]
                for node in queue:
                    for nxt in following.get(node, ()):
                        if nxt not in seen:
                            seen.add(nxt)
                            queue.append(nxt)
                pairs |= {(start, node) for node in seen}
            self.walked[key] = pairs
        return self.walked[key]

    def extend(
        self, pattern: Sequence[str], solution: tuple[dict[str, str], list[Triple]], when: float
    ) -> list[tuple[dict[str, str], list[Triple]]]:
        bindings, used = solution
        found = []
        if pattern[1].endswith("+"):
            first = pattern[0] if not self.is_variable(pattern[0]) else bindings.get(pattern[0])
            last = pattern[2] if not self.is_variable(pattern[2]) else bindings.get(pattern[2])
            pairs = [
                pair
                for pair in self.closure(pattern[1][:-1], when)
                if first in (None, "?", pair[0]) and last in (None, "?", pair[1])
            ]
            for pair in sorted(pairs):
                merged = self.unify((pattern[0], pattern[2]), pair, bindings)
                if merged is not None:
                    found.append((merged, used))
            return found
        for triple in self.triples_at(when):
            merged = self.unify(pattern, triple, bindings)
            if merged is not None:
                found.append((merged, [*used, triple]))
        return found

    def solutions(
        self, patterns: Sequence[Sequence[str]], when: float
    ) -> list[tuple[dict[str, str], list[Triple]]]:
        found: list[tuple[dict[str, str], list[Triple]]] = [({}, [])]
        for pattern in patterns:
            found = [more for solution in found for more in self.extend(pattern, solution, when)]
        return found

    def rows(self, patterns: Sequence[Sequence[str]], select: list[str], when: float) -> list[Any]:
        found = self.solutions(patterns, when)
        return sorted({tuple(b[name] for name in select) for b, _ in found})

    def query(self, patterns: list[list[str]], select: list[str]) -> list[list[str]]:
        return [list(row) for row in self.rows(patterns, select, CURRENT)]

    # --- level 4
    def record(self, subject: str, predicate: str, obj: str, source: str, time: int) -> bool:
        self.now = time
        spans = self.spans.setdefault((subject, predicate, obj), [])
        if spans and spans[-1][1] == FOREVER:
            if source and source not in [name for name, _ in spans[-1][2]]:
                spans[-1][2].append((source, time))
            return False
        spans.append([time, FOREVER, [(source, time)] if source else []])
        return True

    def retract(self, subject: str, predicate: str, obj: str, time: int) -> bool:
        self.now = time
        spans = self.spans.get((subject, predicate, obj), [])
        if not spans or spans[-1][1] != FOREVER:
            return False
        spans[-1][1] = time
        return True

    def query_as_of(self, patterns: list[list[str]], select: list[str], time: int) -> list[Any]:
        return [list(row) for row in self.rows(patterns, select, time)]

    def sources_as_of(
        self, patterns: list[list[str]], select: list[str], time: int
    ) -> list[list[str]]:
        found = self.solutions(patterns, time)
        answer = []
        for row in self.rows(patterns, select, time):
            names: set[str] = set()
            for bindings, used in found:
                if tuple(bindings[name] for name in select) == row:
                    for triple in used:
                        span = self.span_at(triple, time)
                        if span is not None:
                            names |= {name for name, at in span[2] if at <= time}
            answer.append(sorted(names))
        return answer


# ------------------------------------------------------------------ level 1 mistakes
class AddCountsDuplicates(Model):
    """Counts a triple again when it is added twice, and says 'added' every time."""

    def __init__(self) -> None:
        super().__init__()
        self.extra = 0

    def add(self, subject: str, predicate: str, obj: str) -> bool:
        added = super().add(subject, predicate, obj)
        self.extra += 0 if added else 1
        return True

    def size(self) -> int:
        return super().size() + self.extra


class RemoveOfAMissingTripleIsTrue(Model):
    """Says 'removed' for a triple that was not there."""

    def remove(self, subject: str, predicate: str, obj: str) -> bool:
        super().remove(subject, predicate, obj)
        return True


class RemoveIsIgnored(Model):
    """Reports a removal and keeps the triple."""

    def remove(self, subject: str, predicate: str, obj: str) -> bool:
        return (subject, predicate, obj) in self.triples_at(CURRENT)


class RemoveTakesEveryTripleOfTheSubject(Model):
    """Removes all the triples of the subject."""

    def remove(self, subject: str, predicate: str, obj: str) -> bool:
        gone = super().remove(subject, predicate, obj)
        if gone:
            for triple in self.triples_at(CURRENT):
                if triple[0] == subject:
                    super().remove(*triple)
        return gone


class AddAfterRemoveIsRefused(Model):
    """Says 'already there' for a triple that was removed earlier."""

    def add(self, subject: str, predicate: str, obj: str) -> bool:
        if (subject, predicate, obj) in self.spans and not self.present(
            (subject, predicate, obj), CURRENT
        ):
            return False
        return super().add(subject, predicate, obj)


class SizeCountsRemovedTriples(Model):
    """Counts the triples ever added."""

    def size(self) -> int:
        return len(self.spans)


class MatchInInsertionOrder(Model):
    """Lists the triples in the order they were added."""

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        wanted = (subject, predicate, obj)
        return [
            list(triple)
            for triple in self.triples_at(CURRENT)
            if all(w == "?" or w == t for w, t in zip(wanted, triple, strict=True))
        ]


class MatchSortedByObjectFirst(Model):
    """Sorts by object, then subject, then predicate."""

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        return sorted(super().match(subject, predicate, obj), key=lambda t: (t[2], t[0], t[1]))


class MatchIgnoresTheObject(Model):
    """Leaves the object out of the pattern."""

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        return super().match(subject, predicate, "?")


class MatchIgnoresThePredicate(Model):
    """Leaves the predicate out of the pattern when the subject and object are given."""

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        if "?" not in (subject, obj):
            predicate = "?"
        return super().match(subject, predicate, obj)


class MatchAllIsEmpty(Model):
    """Answers nothing when every position is a wildcard."""

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        if (subject, predicate, obj) == ("?", "?", "?"):
            return []
        return super().match(subject, predicate, obj)


class WildcardIsAnotherTerm(Model):
    """Compares the wildcard with the stored terms, so that only a term spelled '?' matches."""

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        wanted = (subject, predicate, obj)
        return [
            list(triple)
            for triple in sorted(self.triples_at(CURRENT))
            if all(w == t for w, t in zip(wanted, triple, strict=True))
        ]


class MatchIsCaseInsensitive(Model):
    """Compares terms without their case."""

    def match(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        wanted = (subject.lower(), predicate.lower(), obj.lower())
        return [
            list(triple)
            for triple in sorted(self.triples_at(CURRENT))
            if all(w == "?" or w == t.lower() for w, t in zip(wanted, triple, strict=True))
        ]


# ------------------------------------------------------------------ level 2 mistakes
class JoinIgnoresSharedVariables(Model):
    """Combines the answers of the patterns without checking that a shared variable agrees."""

    def unify(self, tokens, values, bindings):  # type: ignore[no-untyped-def]
        merged = dict(bindings)
        for token, value in zip(tokens, values, strict=True):
            if token == "?":
                continue
            if self.is_variable(token):
                merged[token] = value
            elif token != value:
                return None
        return merged


class RepeatedVariableInOnePatternIgnored(Model):
    """Lets a variable that appears twice in one pattern take two different values."""

    def unify(self, tokens, values, bindings):  # type: ignore[no-untyped-def]
        merged = dict(bindings)
        seen_here: dict[str, str] = {}
        for token, value in zip(tokens, values, strict=True):
            if token == "?":
                continue
            if self.is_variable(token):
                if token in bindings and bindings[token] != value:
                    return None
                if token in seen_here:
                    continue
                seen_here[token] = value
                merged[token] = value
            elif token != value:
                return None
        return merged


class VariablesKeepOnePerPosition(Model):
    """Joins a variable only with variables in the same position of other patterns."""

    def unify(self, tokens, values, bindings):  # type: ignore[no-untyped-def]
        merged = dict(bindings)
        for place, (token, value) in enumerate(zip(tokens, values, strict=True)):
            if token == "?":
                continue
            if self.is_variable(token):
                key = f"{token}@{place if len(tokens) == 3 else place * 2}"
                if merged.setdefault(key, value) != value:
                    return None
                merged[token] = value
            elif token != value:
                return None
        return merged


class RowsKeepDuplicates(Model):
    """Lists a row once for every way to reach it."""

    def rows(self, patterns, select, when):  # type: ignore[no-untyped-def]
        found = self.solutions(patterns, when)
        return sorted(tuple(b[name] for name in select) for b, _ in found)


class RowsInFirstAppearanceOrder(Model):
    """Orders the columns by the first appearance of each variable, not by `select`."""

    def rows(self, patterns, select, when):  # type: ignore[no-untyped-def]
        appearance = [t for p in patterns for t in (p[0], p[1], p[2]) if self.is_variable(t)]
        order = sorted(select, key=appearance.index)
        found = self.solutions(patterns, when)
        return sorted({tuple(b[name] for name in order) for b, _ in found})


class RowsInDiscoveryOrder(Model):
    """Leaves the rows in the order the join found them."""

    def rows(self, patterns, select, when):  # type: ignore[no-untyped-def]
        found = self.solutions(patterns, when)
        seen: list[tuple[str, ...]] = []
        for bindings, _ in found:
            row = tuple(bindings[name] for name in select)
            if row not in seen:
                seen.append(row)
        return seen


class RowsSortedByTheFirstColumnOnly(Model):
    """Sorts by the first column and leaves ties in the order the join found them."""

    def rows(self, patterns, select, when):  # type: ignore[no-untyped-def]
        found = self.solutions(patterns, when)
        seen: list[tuple[str, ...]] = []
        for bindings, _ in found:
            row = tuple(bindings[name] for name in select)
            if row not in seen:
                seen.append(row)
        return sorted(seen, key=lambda row: row[0])


class GroundPatternIsNotAFilter(Model):
    """Skips a pattern that has no variable, even when its triple is absent."""

    def extend(self, pattern, solution, when):  # type: ignore[no-untyped-def]
        if not any(self.is_variable(t) or t == "?" for t in pattern):
            return [solution]
        return super().extend(pattern, solution, when)


class BareWildcardBindsLikeAVariable(Model):
    """Treats every bare '?' as one shared variable."""

    def unify(self, tokens, values, bindings):  # type: ignore[no-untyped-def]
        merged = dict(bindings)
        for token, value in zip(tokens, values, strict=True):
            if token.startswith("?"):
                if merged.setdefault(token, value) != value:
                    return None
            elif token != value:
                return None
        return merged


class PredicateVariableIsAnotherTerm(Model):
    """Reads a variable in the predicate position as a literal term."""

    def unify(self, tokens, values, bindings):  # type: ignore[no-untyped-def]
        if len(tokens) == 3 and self.is_variable(tokens[1]):
            return None
        return super().unify(tokens, values, bindings)


class QueryStopsAtTheFirstEmptyPattern(Model):
    """Ignores a pattern with no match instead of making the answer empty."""

    def solutions(self, patterns, when):  # type: ignore[no-untyped-def]
        found = [({}, [])]
        for pattern in patterns:
            more = [m for solution in found for m in self.extend(pattern, solution, when)]
            if more:
                found = more
        return found


# ------------------------------------------------------------------ level 3 mistakes
class PathIncludesTheStart(Model):
    """Reads p+ as p*, so that the start is always in the answer."""

    def closure(self, predicate: str, when: float) -> set[tuple[str, str]]:
        pairs = super().closure(predicate, when)
        nodes = {n for pair in self.edges(predicate, when) for n in pair}
        return pairs | {(n, n) for n in nodes}


class PathIsOneHop(Model):
    """Follows the predicate once."""

    def closure(self, predicate: str, when: float) -> set[tuple[str, str]]:
        return self.edges(predicate, when)


class PathIsAtMostTwoHops(Model):
    """Follows the predicate once or twice."""

    def closure(self, predicate: str, when: float) -> set[tuple[str, str]]:
        edges = self.edges(predicate, when)
        return edges | {(a, d) for a, b in edges for c, d in edges if b == c}


class PathNeverReturnsToTheStart(Model):
    """Marks the start as visited, so that a cycle never brings the walk back to it."""

    def closure(self, predicate: str, when: float) -> set[tuple[str, str]]:
        return {(a, b) for a, b in super().closure(predicate, when) if a != b}


class PathFollowsEdgesBothWays(Model):
    """Walks the predicate in both directions."""

    def edges(self, predicate: str, when: float) -> set[tuple[str, str]]:
        forward = super().edges(predicate, when)
        return forward | {(b, a) for a, b in forward}


class PathFollowsAnyPredicate(Model):
    """Walks every predicate, not just the one named."""

    def edges(self, predicate: str, when: float) -> set[tuple[str, str]]:
        return {(s, o) for s, _, o in self.triples_at(when)}


class PathWithoutAVisitedSet(Model):
    """Walks recursively and never remembers a node, so that a cycle never ends."""

    def closure(self, predicate: str, when: float) -> set[tuple[str, str]]:
        edges = self.edges(predicate, when)

        def below(node: str) -> set[str]:
            found: set[str] = set()
            for first, second in edges:
                if first == node:
                    found.add(second)
                    found |= below(second)
            return found

        return {(a, b) for a in {a for a, _ in edges} for b in below(a)}


class PathWithTwoOpenEndsIsEmpty(Model):
    """Answers nothing when neither end of the path is known."""

    def extend(self, pattern, solution, when):  # type: ignore[no-untyped-def]
        if pattern[1].endswith("+"):
            ends = (self.value(pattern[0], solution[0]), self.value(pattern[2], solution[0]))
            if ends == (None, None):
                return []
        return super().extend(pattern, solution, when)

    def value(self, token: str, bindings: dict[str, str]) -> str | None:
        if token == "?" or (self.is_variable(token) and token not in bindings):
            return None
        return bindings.get(token, token)


class PathIgnoresASecondVariable(Model):
    """Lets x p+ x match any pair when both ends are the same variable."""

    def unify(self, tokens, values, bindings):  # type: ignore[no-untyped-def]
        if len(tokens) == 2 and tokens[0] == tokens[1] and self.is_variable(tokens[0]):
            return {**bindings, tokens[0]: values[0]}
        return super().unify(tokens, values, bindings)


class PathCountsSelfLoopsOnlyWithAnotherEdge(Model):
    """Skips a node whose only edge points at itself."""

    def edges(self, predicate: str, when: float) -> set[tuple[str, str]]:
        return {(s, o) for s, o in super().edges(predicate, when) if s != o}


# ------------------------------------------------------------------ level 4 mistakes
class RemoveForgetsTheHistory(Model):
    """Deletes the triple from every point in time when it is removed."""

    def retract(self, subject: str, predicate: str, obj: str, time: int) -> bool:
        gone = super().retract(subject, predicate, obj, time)
        if gone:
            del self.spans[(subject, predicate, obj)]
        return gone


class SpanEndsAfterTheRetractionTime(Model):
    """Keeps the triple present at the moment it is retracted."""

    def present(self, triple: Triple, when: float) -> bool:
        return any(start <= when <= end for start, end, _ in self.spans.get(triple, []))

    def span_at(self, triple: Triple, when: float) -> list[Any] | None:
        for span in self.spans.get(triple, []):
            if span[0] <= when <= span[1]:
                return span
        return None


class SpanStartsAfterTheRecordTime(Model):
    """Shows a triple only after the moment it was recorded."""

    def present(self, triple: Triple, when: float) -> bool:
        return any(start < when < end for start, end, _ in self.spans.get(triple, []))

    def span_at(self, triple: Triple, when: float) -> list[Any] | None:
        for span in self.spans.get(triple, []):
            if span[0] < when < span[1]:
                return span
        return None


class AsOfIgnoresRetractions(Model):
    """Shows every triple ever recorded before the time."""

    def present(self, triple: Triple, when: float) -> bool:
        return any(start <= when for start, _, _ in self.spans.get(triple, []))

    def span_at(self, triple: Triple, when: float) -> list[Any] | None:
        before = [s for s in self.spans.get(triple, []) if s[0] <= when]
        return before[-1] if before else None


class RecordOfAPresentTripleReturnsTrue(Model):
    """Says 'new' when a second source records a triple that is present."""

    def record(self, subject: str, predicate: str, obj: str, source: str, time: int) -> bool:
        super().record(subject, predicate, obj, source, time)
        return True


class RecordOfAPresentTripleReplacesTheSources(Model):
    """Keeps only the latest source of a triple that several sources recorded."""

    def record(self, subject: str, predicate: str, obj: str, source: str, time: int) -> bool:
        spans = self.spans.get((subject, predicate, obj), [])
        fresh = super().record(subject, predicate, obj, source, time)
        if not fresh and source:
            spans[-1][2] = [(source, time)]
        return fresh


class SourcesRepeated(Model):
    """Lists a source again each time it records the same triple."""

    def record(self, subject: str, predicate: str, obj: str, source: str, time: int) -> bool:
        spans = self.spans.get((subject, predicate, obj), [])
        if spans and spans[-1][1] == FOREVER and source:
            self.now = time
            spans[-1][2].append((source, time))
            return False
        return super().record(subject, predicate, obj, source, time)

    def sources_as_of(self, patterns, select, time):  # type: ignore[no-untyped-def]
        found = self.solutions(patterns, time)
        answer = []
        for row in self.rows(patterns, select, time):
            names: list[str] = []
            for bindings, used in found:
                if tuple(bindings[name] for name in select) == row:
                    for triple in used:
                        span = self.span_at(triple, time)
                        if span is not None:
                            names += [name for name, at in span[2] if at <= time]
            answer.append(sorted(names))
        return answer


class SourcesIgnoreTheirTime(Model):
    """Lists the sources that recorded the triple later than the time asked for."""

    def sources_as_of(self, patterns, select, time):  # type: ignore[no-untyped-def]
        found = self.solutions(patterns, time)
        answer = []
        for row in self.rows(patterns, select, time):
            names: set[str] = set()
            for bindings, used in found:
                if tuple(bindings[name] for name in select) == row:
                    for triple in used:
                        span = self.span_at(triple, time)
                        if span is not None:
                            names |= {name for name, _ in span[2]}
            answer.append(sorted(names))
        return answer


class SourcesFromEarlierSpansToo(Model):
    """Keeps the sources of an earlier span when a triple is recorded again after a removal."""

    def record(self, subject: str, predicate: str, obj: str, source: str, time: int) -> bool:
        spans = self.spans.get((subject, predicate, obj), [])
        earlier = list(spans[-1][2]) if spans else []
        fresh = super().record(subject, predicate, obj, source, time)
        if fresh and earlier:
            self.spans[(subject, predicate, obj)][-1][2] = (
                earlier + self.spans[(subject, predicate, obj)][-1][2]
            )
        return fresh


class SourcesListTheEmptySource(Model):
    """Lists the empty source, the one that means 'no source'."""

    def record(self, subject: str, predicate: str, obj: str, source: str, time: int) -> bool:
        self.now = time
        spans = self.spans.setdefault((subject, predicate, obj), [])
        if spans and spans[-1][1] == FOREVER:
            if source not in [name for name, _ in spans[-1][2]]:
                spans[-1][2].append((source, time))
            return False
        spans.append([time, FOREVER, [(source, time)]])
        return True


class SourcesInTheOrderRecorded(Model):
    """Lists the sources in the order they recorded the triple instead of sorted."""

    def sources_as_of(self, patterns, select, time):  # type: ignore[no-untyped-def]
        found = self.solutions(patterns, time)
        answer = []
        for row in self.rows(patterns, select, time):
            names: list[str] = []
            for bindings, used in found:
                if tuple(bindings[name] for name in select) == row:
                    for triple in used:
                        span = self.span_at(triple, time)
                        if span is not None:
                            for name, at in span[2]:
                                if at <= time and name not in names:
                                    names.append(name)
            answer.append(names)
        return answer


class SourcesOfTheFirstPatternOnly(Model):
    """Lists the sources of the first triple of each answer."""

    def solutions(self, patterns, when):  # type: ignore[no-untyped-def]
        return [(b, used[:1]) for b, used in super().solutions(patterns, when)]


class SourcesShareAllRows(Model):
    """Gives every row the sources of all the rows."""

    def sources_as_of(self, patterns, select, time):  # type: ignore[no-untyped-def]
        rows = super().sources_as_of(patterns, select, time)
        everyone = sorted({name for names in rows for name in names})
        return [everyone for _ in rows]


class SourcesOfOneSolutionOnly(Model):
    """Gives a row the sources of the first way to reach it, not of all the ways."""

    def sources_as_of(self, patterns, select, time):  # type: ignore[no-untyped-def]
        found = self.solutions(patterns, time)
        answer = []
        for row in self.rows(patterns, select, time):
            first = next(used for b, used in found if tuple(b[name] for name in select) == row)
            names: set[str] = set()
            for triple in first:
                span = self.span_at(triple, time)
                if span is not None:
                    names |= {name for name, at in span[2] if at <= time}
            answer.append(sorted(names))
        return answer


class RetractOfAMissingTripleIsTrue(Model):
    """Says 'closed' for a triple that is not present."""

    def retract(self, subject: str, predicate: str, obj: str, time: int) -> bool:
        super().retract(subject, predicate, obj, time)
        return True


class AddIgnoresTheClock(Model):
    """Records an `add` at time 0 instead of the latest time."""

    def add(self, subject: str, predicate: str, obj: str) -> bool:
        now = self.now
        fresh = self.record(subject, predicate, obj, "", 0)
        self.now = now
        return fresh


class RemoveIgnoresTheClock(Model):
    """Retracts a `remove` at time 0 instead of the latest time."""

    def remove(self, subject: str, predicate: str, obj: str) -> bool:
        now = self.now
        gone = self.retract(subject, predicate, obj, 0)
        self.now = now
        return gone


class AddDoesNotMoveTheClock(Model):
    """Leaves the clock where `add` found it, instead of at the time of the last record."""

    def record(self, subject: str, predicate: str, obj: str, source: str, time: int) -> bool:
        now = self.now
        fresh = super().record(subject, predicate, obj, source, time)
        self.now = now
        return fresh


class RetractDoesNotMoveTheClock(Model):
    """Leaves the clock where it was when a triple is retracted."""

    def retract(self, subject: str, predicate: str, obj: str, time: int) -> bool:
        now = self.now
        gone = super().retract(subject, predicate, obj, time)
        self.now = now
        return gone


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
    except (IndexError, KeyError, ValueError, TypeError, RecursionError, StopIteration):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_a_hidden_case_holds_a_path_through_a_cycle():
    for case in HIDDEN_CASES:
        wanted = [op for op in case["ops"] if op == "query"]
        if wanted and any(
            pattern[1].endswith("+")
            for op, arguments in zip(case["ops"], case["args"], strict=True)
            if op == "query"
            for pattern in arguments[0]
        ):
            return
    pytest.fail("no hidden case queries a path")


def test_the_generated_case_loads_a_store_of_the_largest_size():
    generated = [case for case in CASES if "generate" in case]
    assert [case["generate"]["n"] for case in generated] == [100000]


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2
