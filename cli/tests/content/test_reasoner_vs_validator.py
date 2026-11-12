"""reasoner-vs-validator promises that its hidden cases catch the classic mistakes of reading one
set of facts as an open-world reasoner and as a closed-world validator: rules left out or applied
once, domain and range read the wrong way round or taken as checks, a transitive or inverse link
missed, a clash reported twice or not through the class hierarchy, a validator that quietly reads
the inferred triples, and a comparison that says the wrong thing. These tests replay every case
against a model of the knowledge base written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0318-reasoner-vs-validator"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

TYPE = "rdf:type"
SUB = "rdfs:subClassOf"
DOMAIN = "rdfs:domain"
RANGE = "rdfs:range"
TRANSITIVE = "owl:TransitiveProperty"
INVERSE = "owl:inverseOf"
DISJOINT = "owl:disjointWith"
MIN, MAX, CLASS = (
    "sh:MinCountConstraintComponent",
    "sh:MaxCountConstraintComponent",
    "sh:ClassConstraintComponent",
)

Triple = tuple[str, str, str]


class Model:
    """The knowledge base as the statement words it: a list of rules applied to a set of triples
    until nothing changes, and a validator that reads the asserted list. Each mistake below
    overrides one rule or one method."""

    def __init__(self) -> None:
        self.asserted: list[Triple] = []
        self.shapes: dict[str, str] = {}
        self.props: dict[str, dict[str, tuple[int, int, str]]] = {}

    # --- the rules, one method each
    def rules(self) -> list[Callable[[set[Triple]], set[Triple]]]:
        return [
            self.subclass_is_transitive,
            self.members_climb,
            self.domain_rule,
            self.range_rule,
            self.transitive_rule,
            self.inverse_rule,
        ]

    def subclass_is_transitive(self, ts: set[Triple]) -> set[Triple]:
        return {
            (c, SUB, e) for c, p, d in ts if p == SUB for d2, q, e in ts if q == SUB and d2 == d
        }

    def members_climb(self, ts: set[Triple]) -> set[Triple]:
        return {
            (x, TYPE, d) for c, p, d in ts if p == SUB for x, q, c2 in ts if q == TYPE and c2 == c
        }

    def domain_rule(self, ts: set[Triple]) -> set[Triple]:
        return {(x, TYPE, c) for p, r, c in ts if r == DOMAIN for x, q, _ in ts if q == p}

    def range_rule(self, ts: set[Triple]) -> set[Triple]:
        return {(y, TYPE, c) for p, r, c in ts if r == RANGE for _, q, y in ts if q == p}

    def transitive_properties(self, ts: set[Triple]) -> set[str]:
        return {s for s, p, o in ts if p == TYPE and o == TRANSITIVE}

    def transitive_rule(self, ts: set[Triple]) -> set[Triple]:
        props = self.transitive_properties(ts)
        return {(x, p, z) for x, p, y in ts if p in props for y2, q, z in ts if q == p and y2 == y}

    def inverse_rule(self, ts: set[Triple]) -> set[Triple]:
        found = set()
        for p1, r, p2 in ts:
            if r == INVERSE:
                found |= {(y, p2, x) for x, p, y in ts if p == p1}
                found |= {(y, p1, x) for x, p, y in ts if p == p2}
        return found

    def closure_set(self) -> set[Triple]:
        triples = set(self.asserted)
        while True:
            new = set().union(*(rule(triples) for rule in self.rules()))
            if new <= triples:
                return triples
            triples |= new

    # --- level 1
    def add(self, subject: str, predicate: str, obj: str) -> bool:
        triple = (subject, predicate, obj)
        if triple in self.asserted:
            return False
        self.asserted.append(triple)
        return True

    def order(self, items: Any) -> list[Any]:
        return sorted(items)

    def closure(self, subject: str, predicate: str, obj: str) -> list[list[str]]:
        def fits(want: str, got: str) -> bool:
            return want in ("?", got)

        found = [
            t
            for t in self.closure_set()
            if fits(subject, t[0]) and fits(predicate, t[1]) and fits(obj, t[2])
        ]
        return [list(t) for t in self.order(found)]

    def types_in(self, ts: set[Triple], resource: str) -> set[str]:
        return {o for s, p, o in ts if s == resource and p == TYPE}

    def types(self, resource: str) -> list[str]:
        return self.order(self.types_in(self.closure_set(), resource))

    def instances(self, class_name: str) -> list[str]:
        return self.order({s for s, p, o in self.closure_set() if p == TYPE and o == class_name})

    def supers_in(self, ts: set[Triple], class_name: str) -> set[str]:
        return {o for s, p, o in ts if s == class_name and p == SUB}

    def super_classes(self, class_name: str) -> list[str]:
        return self.order(self.supers_in(self.closure_set(), class_name) - {class_name})

    # --- level 2
    def ask(self, subject: str, predicate: str, obj: str) -> str:
        ts = self.closure_set()
        if (subject, predicate, obj) in ts:
            return "entailed"
        if predicate == TYPE and self.would_clash(ts, subject, obj):
            return "contradicted"
        return "unknown"

    # --- level 3
    def disjoint_pairs(self, ts: set[Triple]) -> set[tuple[str, str]]:
        return {(min(a, b), max(a, b)) for a, p, b in ts if p == DISJOINT}

    def would_clash(self, ts: set[Triple], subject: str, cls: str) -> bool:
        have = self.types_in(ts, subject)
        coming = {cls} | self.supers_in(ts, cls)
        return any(
            (a in have and b in coming) or (b in have and a in coming)
            for a, b in self.disjoint_pairs(ts)
        )

    def clash_types(self, ts: set[Triple], resource: str) -> set[str]:
        return self.types_in(ts, resource)

    def inconsistencies(self) -> list[list[str]]:
        ts = self.closure_set()
        resources = {s for s, _, _ in ts}
        rows = {
            (r, a, b)
            for a, b in self.disjoint_pairs(ts)
            for r in resources
            if {a, b} <= self.clash_types(ts, r)
        }
        return [list(row) for row in self.order(rows)]

    # --- level 4
    def add_shape(self, shape: str, target_class: str) -> bool:
        if shape in self.shapes:
            return False
        self.shapes[shape] = target_class
        self.props[shape] = {}
        return True

    def add_property(
        self, shape: str, path: str, min_count: int, max_count: int, value_class: str
    ) -> bool:
        if shape not in self.shapes or path in self.props[shape]:
            return False
        self.props[shape][path] = (min_count, max_count, value_class)
        return True

    def data(self) -> list[Triple]:
        """The triples the validator reads."""
        return self.asserted

    def shacl_types(self, node: str) -> set[str]:
        data = self.data()
        found = {o for s, p, o in data if s == node and p == TYPE}
        grew = True
        while grew:
            grew = False
            for s, p, o in data:
                if p == SUB and s in found and o not in found:
                    found.add(o)
                    grew = True
        return found

    def focus_nodes(self, target: str) -> set[str]:
        return {s for s, p, _ in self.data() if p == TYPE and target in self.shacl_types(s)}

    def values_of(self, node: str, path: str) -> set[str]:
        return {o for s, p, o in self.data() if s == node and p == path}

    def too_few(self, count: int, minimum: int) -> bool:
        return count < minimum

    def too_many(self, count: int, maximum: int) -> bool:
        return maximum != -1 and count > maximum

    def bad_value(self, value: str, value_class: str) -> bool:
        return value_class not in self.shacl_types(value)

    def class_rows(self, focus: str, shape: str, path: str, value_class: str) -> set[tuple]:
        if value_class == "":
            return set()
        return {
            (focus, shape, path, CLASS, v)
            for v in self.values_of(focus, path)
            if self.bad_value(v, value_class)
        }

    def violation_set(self) -> set[tuple[str, str, str, str, str]]:
        rows: set[tuple[str, str, str, str, str]] = set()
        for shape, target in self.shapes.items():
            for focus in self.focus_nodes(target):
                for path, (low, high, value_class) in self.props[shape].items():
                    count = len(self.values_of(focus, path))
                    if self.too_few(count, low):
                        rows.add((focus, shape, path, MIN, ""))
                    if self.too_many(count, high):
                        rows.add((focus, shape, path, MAX, ""))
                    rows |= self.class_rows(focus, shape, path, value_class)
        return rows

    def validate(self) -> list[list[str]]:
        return [list(row) for row in self.order(self.violation_set())]

    def reasoner_says(self, row: tuple[str, str, str, str, str]) -> str:
        focus, shape, path, component, value = row
        ts = self.closure_set()
        low, _, value_class = self.props[shape][path]
        if component == MAX:
            return "no-error"
        if component == MIN:
            return (
                "entailed"
                if len({o for s, p, o in ts if s == focus and p == path}) >= low
                else "unknown"
            )
        return "entailed" if (value, TYPE, value_class) in ts else "unknown"

    def contrast(self) -> list[list[str]]:
        return [[*row, self.reasoner_says(row)] for row in self.order(self.violation_set())]


# ------------------------------------------------------------------ level 1 mistakes
class NoSubclassTransitivity(Model):
    """Never chains subclass links."""

    def subclass_is_transitive(self, ts: set[Triple]) -> set[Triple]:
        return set()


class NoTypeInheritance(Model):
    """Leaves an instance in its own class only."""

    def members_climb(self, ts: set[Triple]) -> set[Triple]:
        return set()


class SubclassDirectionReversed(Model):
    """Moves instances down the hierarchy instead of up."""

    def members_climb(self, ts: set[Triple]) -> set[Triple]:
        return {
            (x, TYPE, c) for c, p, d in ts if p == SUB for x, q, d2 in ts if q == TYPE and d2 == d
        }


class SuperClassesIncludeTheClass(Model):
    """Lists a class as its own superclass when a cycle makes it one."""

    def super_classes(self, class_name: str) -> list[str]:
        return self.order(self.supers_in(self.closure_set(), class_name))


class EveryClassIsItsOwnSubclass(Model):
    """Applies the reflexivity rule that the subset leaves out."""

    def subclass_is_transitive(self, ts: set[Triple]) -> set[Triple]:
        classes = {t[0] for t in ts if t[1] == SUB} | {t[2] for t in ts if t[1] == SUB}
        return super().subclass_is_transitive(ts) | {(c, SUB, c) for c in classes}


class AddReportsTheClosure(Model):
    """Says a triple is not new when it is already inferred."""

    def add(self, subject: str, predicate: str, obj: str) -> bool:
        if (subject, predicate, obj) in self.closure_set():
            self.asserted.append((subject, predicate, obj))
            return False
        return super().add(subject, predicate, obj)


class SortsIgnoringCase(Model):
    """Orders texts without regard to case."""

    def order(self, items: Any) -> list[Any]:
        return sorted(
            items,
            key=lambda item: (
                [str(part).lower() for part in item]
                if isinstance(item, tuple)
                else str(item).lower()
            ),
        )


class InstancesOnlyAsserted(Model):
    """Lists only the directly asserted instances."""

    def instances(self, class_name: str) -> list[str]:
        return self.order({s for s, p, o in self.asserted if p == TYPE and o == class_name})


# ------------------------------------------------------------------ level 2 mistakes
class DomainAndRangeSwapped(Model):
    """Types the object by the domain and the subject by the range."""

    def domain_rule(self, ts: set[Triple]) -> set[Triple]:
        return {(y, TYPE, c) for p, r, c in ts if r == DOMAIN for _, q, y in ts if q == p}

    def range_rule(self, ts: set[Triple]) -> set[Triple]:
        return {(x, TYPE, c) for p, r, c in ts if r == RANGE for x, q, _ in ts if q == p}


class OnlyTheFirstDomain(Model):
    """Applies the first domain of a property and ignores the others."""

    def domain_rule(self, ts: set[Triple]) -> set[Triple]:
        first: dict[str, str] = {}
        for p, r, c in sorted(self.asserted):
            if r == DOMAIN:
                first.setdefault(p, c)
        return {(x, TYPE, c) for p, c in first.items() for x, q, _ in ts if q == p}


class NoDomainOrRange(Model):
    """Treats domain and range as documentation."""

    def domain_rule(self, ts: set[Triple]) -> set[Triple]:
        return set()

    def range_rule(self, ts: set[Triple]) -> set[Triple]:
        return set()


class InferredTypesAreNotClimbed(Model):
    """Passes only the asserted types up the hierarchy."""

    def members_climb(self, ts: set[Triple]) -> set[Triple]:
        asserted = set(self.asserted)
        return {
            (x, TYPE, d)
            for c, p, d in ts
            if p == SUB
            for x, q, c2 in ts
            if q == TYPE and c2 == c and (x, q, c2) in asserted
        }


class DomainSkipsTheVocabulary(Model):
    """Applies domain and range only to facts whose predicate is not part of the vocabulary."""

    VOCABULARY = frozenset({TYPE, SUB, DOMAIN, RANGE, INVERSE, DISJOINT, TRANSITIVE})

    def domain_rule(self, ts: set[Triple]) -> set[Triple]:
        return {
            (x, TYPE, c)
            for p, r, c in ts
            if r == DOMAIN and p not in self.VOCABULARY
            for x, q, _ in ts
            if q == p
        }

    def range_rule(self, ts: set[Triple]) -> set[Triple]:
        return {
            (y, TYPE, c)
            for p, r, c in ts
            if r == RANGE and p not in self.VOCABULARY
            for _, q, y in ts
            if q == p
        }


class RangeIsNotInferred(Model):
    """Applies domains and treats ranges as documentation."""

    def range_rule(self, ts: set[Triple]) -> set[Triple]:
        return set()


class AskAnswersNo(Model):
    """Closes the world: what is not entailed is false."""

    def ask(self, subject: str, predicate: str, obj: str) -> str:
        answer = super().ask(subject, predicate, obj)
        return "no" if answer == "unknown" else answer


# ------------------------------------------------------------------ level 3 mistakes
class TransitiveJustOnce(Model):
    """Joins only asserted links, so a chain of three or more stops short."""

    def transitive_rule(self, ts: set[Triple]) -> set[Triple]:
        props = self.transitive_properties(ts)
        base = set(self.asserted)
        return {
            (x, p, z) for x, p, y in ts if p in props for y2, q, z in base if q == p and y2 == y
        }


class TransitiveOnlyDeclaredFirst(Model):
    """Reads transitive declarations from the asserted triples only."""

    def transitive_properties(self, ts: set[Triple]) -> set[str]:
        return {s for s, p, o in self.asserted if p == TYPE and o == TRANSITIVE}


class InverseOneWay(Model):
    """Applies the inverse from the first property to the second only."""

    def inverse_rule(self, ts: set[Triple]) -> set[Triple]:
        return {(y, p2, x) for p1, r, p2 in ts if r == INVERSE for x, p, y in ts if p == p1}


class CycleLinksDropped(Model):
    """Never links a node to itself through a transitive property."""

    def transitive_rule(self, ts: set[Triple]) -> set[Triple]:
        return {t for t in super().transitive_rule(ts) if t[0] != t[2]}


class ClashOnAssertedTypesOnly(Model):
    """Looks for clashes among the directly asserted types."""

    def clash_types(self, ts: set[Triple], resource: str) -> set[str]:
        return {o for s, p, o in self.asserted if s == resource and p == TYPE}


class ClashListedInBothOrders(Model):
    """Lists a pair once for each way it was stated."""

    def disjoint_pairs(self, ts: set[Triple]) -> set[tuple[str, str]]:
        return {(a, b) for a, p, b in ts if p == DISJOINT}


class ClashIgnoresSelfDisjoint(Model):
    """Skips a class that is disjoint with itself."""

    def disjoint_pairs(self, ts: set[Triple]) -> set[tuple[str, str]]:
        return {(a, b) for a, b in super().disjoint_pairs(ts) if a != b}


class AskIgnoresSuperclassesOfTheAsked(Model):
    """Checks only the asked class against the disjoint pairs."""

    def would_clash(self, ts: set[Triple], subject: str, cls: str) -> bool:
        have = self.types_in(ts, subject)
        return any(
            (a in have and b == cls) or (b in have and a == cls) for a, b in self.disjoint_pairs(ts)
        )


class AskContradictedBeatsEntailed(Model):
    """Reports a clash even when the triple is already entailed."""

    def ask(self, subject: str, predicate: str, obj: str) -> str:
        ts = self.closure_set()
        if predicate == TYPE and self.would_clash(ts, subject, obj):
            return "contradicted"
        return super().ask(subject, predicate, obj)


class AskContradictedForOtherPredicates(Model):
    """Applies the clash test to the object of any predicate."""

    def ask(self, subject: str, predicate: str, obj: str) -> str:
        answer = super().ask(subject, predicate, obj)
        if answer == "unknown" and self.would_clash(self.closure_set(), subject, obj):
            return "contradicted"
        return answer


class AskContradictedOnlyOneWay(Model):
    """Reads each disjoint pair in the order it is sorted, held class first."""

    def would_clash(self, ts: set[Triple], subject: str, cls: str) -> bool:
        have = self.types_in(ts, subject)
        coming = {cls} | self.supers_in(ts, cls)
        return any(a in have and b in coming for a, b in self.disjoint_pairs(ts))


# ------------------------------------------------------------------ level 4 mistakes
class ValidatorReadsTheClosure(Model):
    """Validates the inferred graph."""

    def data(self) -> list[Triple]:
        return sorted(self.closure_set())


class FocusNodesFromTheClosure(Model):
    """Targets every term the reasoner types, but counts asserted values."""

    def focus_nodes(self, target: str) -> set[str]:
        return {s for s, p, o in self.closure_set() if p == TYPE and o == target}


class ValuesFromTheClosure(Model):
    """Counts the values the reasoner derives."""

    def values_of(self, node: str, path: str) -> set[str]:
        return {o for s, p, o in self.closure_set() if s == node and p == path}


class TargetIgnoresSubclasses(Model):
    """Targets only the terms asserted to be of the class itself."""

    def focus_nodes(self, target: str) -> set[str]:
        return {s for s, p, o in self.asserted if p == TYPE and o == target}


class ValueClassIgnoresSubclasses(Model):
    """Accepts a value only when it is asserted to be of the class itself."""

    def bad_value(self, value: str, value_class: str) -> bool:
        return (value, TYPE, value_class) not in self.asserted


class ValueClassFromTheClosure(Model):
    """Accepts a value that the reasoner types."""

    def bad_value(self, value: str, value_class: str) -> bool:
        return (value, TYPE, value_class) not in self.closure_set()


class MaxCountOffByOne(Model):
    """Allows one value fewer than the limit."""

    def too_many(self, count: int, maximum: int) -> bool:
        return maximum != -1 and count >= maximum


class MinCountOffByOne(Model):
    """Allows one value fewer than the minimum."""

    def too_few(self, count: int, minimum: int) -> bool:
        return count < minimum - 1


class UnlimitedMeansZero(Model):
    """Reads -1 as a limit of zero values."""

    def too_many(self, count: int, maximum: int) -> bool:
        return count > max(maximum, 0)


class MissingValueIsAClassViolation(Model):
    """Reports a missing value as a violation of the class too."""

    def class_rows(self, focus: str, shape: str, path: str, value_class: str) -> set[tuple]:
        rows = super().class_rows(focus, shape, path, value_class)
        if value_class and not self.values_of(focus, path):
            rows.add((focus, shape, path, CLASS, ""))
        return rows


class MinCountOnlyWhenMaxIsOpen(Model):
    """Drops the minimum when there is a limit."""

    def too_few(self, count: int, minimum: int) -> bool:
        return count < minimum and not any(
            high != -1 for props in self.props.values() for _, high, _ in props.values()
        )


class ContrastMinimumAlwaysUnknown(Model):
    """Says the reasoner does not know, whatever the closure holds."""

    def reasoner_says(self, row: tuple[str, str, str, str, str]) -> str:
        return "unknown" if row[3] == MIN else super().reasoner_says(row)


class ContrastMinimumCountsAsserted(Model):
    """Counts the asserted values for the reasoner too."""

    def reasoner_says(self, row: tuple[str, str, str, str, str]) -> str:
        focus, shape, path, component, _ = row
        if component == MIN:
            low = self.props[shape][path][0]
            have = len(self.values_of(focus, path))
            return "entailed" if have >= low else "unknown"
        return super().reasoner_says(row)


class ContrastClassFromAsserted(Model):
    """Says entailed only for a class that is asserted."""

    def reasoner_says(self, row: tuple[str, str, str, str, str]) -> str:
        if row[3] == CLASS:
            value_class = self.props[row[1]][row[2]][2]
            return "entailed" if (row[4], TYPE, value_class) in self.asserted else "unknown"
        return super().reasoner_says(row)


class ContrastMaximumUnknown(Model):
    """Answers unknown for a limit, instead of no error."""

    def reasoner_says(self, row: tuple[str, str, str, str, str]) -> str:
        return "unknown" if row[3] == MAX else super().reasoner_says(row)


class ShapeCanBeDeclaredTwice(Model):
    """Replaces a shape that exists."""

    def add_shape(self, shape: str, target_class: str) -> bool:
        self.shapes[shape] = target_class
        self.props.setdefault(shape, {})
        return True


class PropertyReplacesTheOldOne(Model):
    """Replaces the constraint of a path that has one."""

    def add_property(
        self, shape: str, path: str, min_count: int, max_count: int, value_class: str
    ) -> bool:
        if shape not in self.shapes:
            return False
        self.props[shape][path] = (min_count, max_count, value_class)
        return True


class ViolationsInTheOrderFound(Model):
    """Lists the violations by shape and path as the shapes were declared."""

    def order(self, items: Any) -> list[Any]:
        items = list(items)
        if items and isinstance(next(iter(items)), tuple) and len(next(iter(items))) == 5:
            declared = list(self.shapes)
            return sorted(
                items, key=lambda row: (declared.index(row[1]), row[2], row[0], row[3], row[4])
            )
        return sorted(items)


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


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_ask_every_answer_of_ask_and_contrast():
    answers = defaultdict(set)
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op in ("ask", "contrast"):
                answers[op].update([got] if isinstance(got, str) else [row[-1] for row in got])
    assert answers["ask"] == {"entailed", "unknown", "contradicted"}
    assert answers["contrast"] == {"entailed", "unknown", "no-error"}
