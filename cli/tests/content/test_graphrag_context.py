"""graphrag-context promises that its hidden cases catch the classic mistakes of building context
from a graph: a neighbourhood measured by the wrong end of a fact, directions followed as if they
were one-way, a score with a wrong halving, a clamp or a tie-break, a token count that rounds the
wrong way, a fill that stops at the first fact that does not fit, a citation path through the wrong
neighbour or the wrong fact, and a text that gets an arrow, a count or a newline wrong. These tests
replay every case against a model of the graph written from the statement, which must give every
expected output, and against that model with one mistake planted at a time, which some hidden case
must fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0321-graphrag-context"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

Fact = tuple[str, str, str]


class Model:
    """The graph as the statement words it. Facts are kept in a list and every answer is found by
    looking at all of them, so each mistake below overrides a single rule."""

    HOP_BASE = 16
    RECENCY_BASE = 16
    MAX_STEPS = 4

    def __init__(self) -> None:
        self.facts: dict[Fact, tuple[int, int]] = {}

    # --- level 1
    def add_fact(self, subject: str, relation: str, obj: str, weight: int, time: int) -> bool:
        if (subject, relation, obj) in self.facts:
            return False
        self.facts[(subject, relation, obj)] = (weight, time)
        return True

    def size(self) -> int:
        return len(self.facts)

    def links(self, subject: str, obj: str) -> list[tuple[str, str]]:
        return [(subject, obj), (obj, subject)]

    def distances(self, entity: str) -> dict[str, int]:
        if not any(entity in (s, o) for s, _, o in self.facts):
            return {}
        far = {entity: 0}
        changed = True
        while changed:
            changed = False
            for subject, _, obj in self.facts:
                for here, there in self.links(subject, obj):
                    if here in far and far[here] + 1 < far.get(there, 10**9):
                        far[there] = far[here] + 1
                        changed = True
        return far

    def hop_of(self, fact: Fact, far: dict[str, int]) -> int | None:
        ends = [far[x] for x in (fact[0], fact[2]) if x in far]
        return min(ends) + 1 if ends else None

    def limit(self, hops: int) -> int:
        return hops

    def within(self, entity: str, hops: int) -> list[tuple[int, Fact]]:
        far = self.distances(entity)
        found = []
        for fact in self.facts:
            hop = self.hop_of(fact, far)
            if hop is not None and hop <= self.limit(hops):
                found.append((hop, fact))
        return self.network_order(found)

    def network_order(self, found: list[tuple[int, Fact]]) -> list[tuple[int, Fact]]:
        return sorted(found)

    def ego_network(self, entity: str, hops: int) -> list[list[str]]:
        return [[*fact, str(hop)] for hop, fact in self.within(entity, hops)]

    # --- level 2
    def steps_of(self, age: int, half_life: int) -> int:
        return min(self.MAX_STEPS, age // half_life)

    def age_of(self, now: int, time: int) -> int:
        return max(0, now - time)

    def hop_factor(self, hop: int) -> int:
        return self.HOP_BASE >> (hop - 1)

    def score(self, hop: int, fact: Fact, now: int, half_life: int) -> int:
        weight, time = self.facts[fact]
        steps = self.steps_of(self.age_of(now, time), half_life)
        return weight * self.hop_factor(hop) * (self.RECENCY_BASE >> steps)

    def rank_key(self, item: tuple[int, int, Fact]) -> tuple[Any, ...]:
        score, hop, fact = item
        return (-score, hop, fact)

    def ranked(
        self, entity: str, hops: int, now: int, half_life: int
    ) -> list[tuple[int, int, Fact]]:
        scored = [
            (self.score(hop, fact, now, half_life), hop, fact)
            for hop, fact in self.within(entity, hops)
        ]
        return sorted(scored, key=self.rank_key)

    def rank_facts(self, entity: str, hops: int, now: int, half_life: int) -> list[list[str]]:
        return [
            [*fact, str(hop), str(score)]
            for score, hop, fact in self.ranked(entity, hops, now, half_life)
        ]

    # --- level 3
    def tokens(self, fact: Fact) -> int:
        return -(-(len(fact[0]) + len(fact[1]) + len(fact[2]) + 2) // 4)

    def fits(self, tokens: int, remaining: int) -> bool:
        return tokens <= remaining

    def fill_order(self, items: list[tuple[int, int, Fact]]) -> list[tuple[int, int, Fact]]:
        return items

    def packed(
        self, entity: str, hops: int, now: int, half_life: int, budget: int
    ) -> list[tuple[int, int, Fact]]:
        remaining = budget
        chosen = []
        for item in self.fill_order(self.ranked(entity, hops, now, half_life)):
            size = self.tokens(item[2])
            if self.fits(size, remaining):
                chosen.append(item)
                remaining -= size
            elif self.stop_at_misfit():
                break
        return chosen

    def stop_at_misfit(self) -> bool:
        return False

    def build_context(
        self, entity: str, hops: int, now: int, half_life: int, budget: int
    ) -> list[list[str]]:
        return [
            [*fact, str(hop), str(score), str(self.tokens(fact))]
            for score, hop, fact in self.packed(entity, hops, now, half_life, budget)
        ]

    # --- level 4
    def parent_pick(self, options: list[tuple[str, Fact]]) -> tuple[str, Fact]:
        return min(options)

    def parent(self, far: dict[str, int], node: str) -> tuple[str, Fact]:
        options = []
        for fact in self.facts:
            if node in (fact[0], fact[2]):
                other = fact[2] if fact[0] == node else fact[0]
                if far.get(other) == far[node] - 1:
                    options.append((other, fact))
        return self.parent_pick(options)

    def near_end(self, far: dict[str, int], fact: Fact) -> str | None:
        ends = [x for x in (fact[0], fact[2]) if x in far]
        return min(ends, key=lambda x: (far[x], x)) if ends else None

    def path(self, far: dict[str, int], entity: str, fact: Fact) -> list[Fact]:
        node = self.near_end(far, fact)
        if node is None:
            return []
        steps: list[Fact] = []
        while node != entity:
            node, step = self.parent(far, node)
            steps.append(step)
        steps.reverse()
        return [*steps, fact]

    def explain(self, entity: str, subject: str, relation: str, obj: str) -> list[list[str]]:
        fact = (subject, relation, obj)
        if fact not in self.facts:
            return []
        return [list(step) for step in self.path(self.distances(entity), entity, fact)]

    def arrow(self, node: str, fact: Fact) -> tuple[str, str]:
        subject, relation, obj = fact
        if node == subject:
            return f" -{relation}-> {obj}", obj
        return f" <-{relation}- {subject}", subject

    def path_text(self, entity: str, steps: list[Fact]) -> str:
        text, node = entity, entity
        for step in steps:
            piece, node = self.arrow(node, step)
            text += piece
        return text

    def header(self, entity: str, chosen: int, used: int, budget: int) -> str:
        return f"Context for {entity} ({chosen} facts, {used} of {budget} tokens)"

    def numbering_start(self) -> int:
        return 1

    def closing(self) -> str:
        return ""

    def render_context(self, entity: str, hops: int, now: int, half_life: int, budget: int) -> str:
        chosen = self.packed(entity, hops, now, half_life, budget)
        used = sum(self.tokens(fact) for _, _, fact in chosen)
        far = self.distances(entity)
        lines = [self.header(entity, len(chosen), used, budget)]
        for number, (_, _, fact) in enumerate(chosen, start=self.numbering_start()):
            text = self.path_text(entity, self.path(far, entity, fact))
            lines.append(f"[{number}] {' '.join(fact)} | path: {text}")
        return "\n".join(lines) + self.closing()


# ------------------------------------------------------------------ level 1 mistakes
class NetworkOfTheInducedSubgraph(Model):
    """Includes the facts whose two ends are within the limit, at the hop of the farther end."""

    def hop_of(self, fact: Fact, far: dict[str, int]) -> int | None:
        if fact[0] not in far or fact[2] not in far:
            return None
        return max(1, max(far[fact[0]], far[fact[2]]))


class HopIsTheFarEndPlusOne(Model):
    """Counts the hop from the farther end."""

    def hop_of(self, fact: Fact, far: dict[str, int]) -> int | None:
        ends = [far[x] for x in (fact[0], fact[2]) if x in far]
        return max(ends) + 1 if ends else None


class ArrowsAreOneWayStreets(Model):
    """Follows each fact from its subject to its object only."""

    def links(self, subject: str, obj: str) -> list[tuple[str, str]]:
        return [(subject, obj)]


class OneHopTooFew(Model):
    """Stops one hop short."""

    def limit(self, hops: int) -> int:
        return hops - 1


class OneHopTooMany(Model):
    """Goes one hop further."""

    def limit(self, hops: int) -> int:
        return hops + 1


class RepeatedFactOverwritesIt(Model):
    """Replaces the weight and the time of a fact that is added again."""

    def add_fact(self, subject: str, relation: str, obj: str, weight: int, time: int) -> bool:
        fresh = (subject, relation, obj) not in self.facts
        self.facts[(subject, relation, obj)] = (weight, time)
        return fresh


class ReverseFactIsADuplicate(Model):
    """Treats b r a as the same fact as a r b."""

    def add_fact(self, subject: str, relation: str, obj: str, weight: int, time: int) -> bool:
        if (obj, relation, subject) in self.facts:
            return False
        return super().add_fact(subject, relation, obj, weight, time)


class RelationIsIgnoredForIdentity(Model):
    """Counts two facts between the same entities as one."""

    def add_fact(self, subject: str, relation: str, obj: str, weight: int, time: int) -> bool:
        if any((s, o) == (subject, obj) for s, _, o in self.facts):
            return False
        return super().add_fact(subject, relation, obj, weight, time)


class NetworkSortedByNamesOnly(Model):
    """Leaves out the hop in the order."""

    def network_order(self, found: list[tuple[int, Fact]]) -> list[tuple[int, Fact]]:
        return sorted(found, key=lambda item: item[1])


class NetworkSortedIgnoringCase(Model):
    """Orders the names without regard to the underscore and the digits' place."""

    def network_order(self, found: list[tuple[int, Fact]]) -> list[tuple[int, Fact]]:
        return sorted(
            found, key=lambda item: (item[0], [part.replace("_", "~") for part in item[1]])
        )


# ------------------------------------------------------------------ level 2 mistakes
class AgeNotClamped(Model):
    """Lets a fact from the future be older than a fact from now."""

    def age_of(self, now: int, time: int) -> int:
        return abs(now - time)


class HalvingsNotCapped(Model):
    """Keeps halving after 4 whole half-lives."""

    MAX_STEPS = 10


class HalvingsCappedAtThree(Model):
    """Stops at 3 halvings."""

    MAX_STEPS = 3


class PartialHalfLifeCounts(Model):
    """Rounds the age up to the next half-life."""

    def steps_of(self, age: int, half_life: int) -> int:
        return min(self.MAX_STEPS, -(-age // half_life))


class AgeRoundedToNearestHalfLife(Model):
    """Rounds the age to the nearest half-life."""

    def steps_of(self, age: int, half_life: int) -> int:
        return min(self.MAX_STEPS, (2 * age + half_life) // (2 * half_life))


class HopFactorIsLinear(Model):
    """Lowers the factor by 3 for each hop instead of halving it."""

    def hop_factor(self, hop: int) -> int:
        return 18 - 3 * hop


class HopIsNotPenalised(Model):
    """Gives every hop the same factor."""

    def hop_factor(self, hop: int) -> int:
        return 16


class TiesBrokenByNamesOnly(Model):
    """Leaves out the hop when scores are equal."""

    def rank_key(self, item: tuple[int, int, Fact]) -> tuple[Any, ...]:
        return (-item[0], item[2])


class TiesGoToTheFartherFact(Model):
    """Puts the farther fact first when scores are equal."""

    def rank_key(self, item: tuple[int, int, Fact]) -> tuple[Any, ...]:
        return (-item[0], -item[1], item[2])


class TiesGoToTheLargerNames(Model):
    """Reverses the order of the names when scores and hops are equal."""

    def rank_key(self, item: tuple[int, int, Fact]) -> tuple[Any, ...]:
        return (-item[0], item[1], tuple(tuple(-ord(c) for c in part) for part in item[2]))


# ------------------------------------------------------------------ level 3 mistakes
class FillStopsAtTheFirstMisfit(Model):
    """Ends the fill at the first fact that does not fit."""

    def stop_at_misfit(self) -> bool:
        return True


class TokensRoundedDown(Model):
    """Counts whole groups of 4 characters only."""

    def tokens(self, fact: Fact) -> int:
        return max(1, (len(fact[0]) + len(fact[1]) + len(fact[2]) + 2) // 4)


class TokensWithoutTheSpaces(Model):
    """Leaves the two spaces out of the count."""

    def tokens(self, fact: Fact) -> int:
        return -(-(len(fact[0]) + len(fact[1]) + len(fact[2])) // 4)


class TokensRoundedToNearest(Model):
    """Rounds to the nearest whole token."""

    def tokens(self, fact: Fact) -> int:
        return max(1, (len(fact[0]) + len(fact[1]) + len(fact[2]) + 2 + 2) // 4)


class TokensAreTheNames(Model):
    """Counts one token per name."""

    def tokens(self, fact: Fact) -> int:
        return 3


class FitNeedsRoomToSpare(Model):
    """Takes a fact only when strictly fewer tokens than the rest are needed."""

    def fits(self, tokens: int, remaining: int) -> bool:
        return tokens < remaining


class SmallestFirstFill(Model):
    """Fills with the smallest facts first."""

    def fill_order(self, items: list[tuple[int, int, Fact]]) -> list[tuple[int, int, Fact]]:
        return sorted(items, key=lambda item: (self.tokens(item[2]), self.rank_key(item)))


class ContextInOrderOfHop(Model):
    """Fills in the order of the network and not of the ranking."""

    def fill_order(self, items: list[tuple[int, int, Fact]]) -> list[tuple[int, int, Fact]]:
        return sorted(items, key=lambda item: (item[1], item[2]))


# ------------------------------------------------------------------ level 4 mistakes
class PathThroughTheLargestNeighbour(Model):
    """Picks the largest name among the neighbours one step closer."""

    def parent_pick(self, options: list[tuple[str, Fact]]) -> tuple[str, Fact]:
        return max(options, key=lambda option: option[0]) if options else min(options)


class PathThroughTheFirstFactAdded(Model):
    """Picks the first fact stored between two entities."""

    def parent_pick(self, options: list[tuple[str, Fact]]) -> tuple[str, Fact]:
        best = min(option[0] for option in options)
        return next(option for option in options if option[0] == best)


class PathThroughTheLargestFact(Model):
    """Picks the largest fact between the chosen neighbour and the entity."""

    def parent_pick(self, options: list[tuple[str, Fact]]) -> tuple[str, Fact]:
        best = min(option[0] for option in options)
        return max((option for option in options if option[0] == best), key=lambda o: o[1])


class PathToTheFartherEnd(Model):
    """Walks to the farther end of the fact, and then back over the fact."""

    def near_end(self, far: dict[str, int], fact: Fact) -> str | None:
        ends = [x for x in (fact[0], fact[2]) if x in far]
        return max(ends, key=lambda x: (far[x], x)) if ends else None


class NearerEndTieGoesToTheLargerName(Model):
    """Breaks a tie of distances by the larger name."""

    def near_end(self, far: dict[str, int], fact: Fact) -> str | None:
        ends = [x for x in (fact[0], fact[2]) if x in far]
        return min(ends, key=lambda x: (far[x], tuple(-ord(c) for c in x))) if ends else None


class PathLeavesOutTheFact(Model):
    """Ends the path at the nearer end of the fact."""

    def path(self, far: dict[str, int], entity: str, fact: Fact) -> list[Fact]:
        return super().path(far, entity, fact)[:-1]


class UnstoredFactHasAPath(Model):
    """Explains a fact that was never stored."""

    def explain(self, entity: str, subject: str, relation: str, obj: str) -> list[list[str]]:
        fact = (subject, relation, obj)
        if fact not in self.facts:
            self.facts[fact] = (1, 0)
            try:
                return super().explain(entity, subject, relation, obj)
            finally:
                del self.facts[fact]
        return super().explain(entity, subject, relation, obj)


class ArrowsAlwaysForward(Model):
    """Writes every step with the forward arrow."""

    def arrow(self, node: str, fact: Fact) -> tuple[str, str]:
        subject, relation, obj = fact
        other = obj if node == subject else subject
        return f" -{relation}-> {other}", other


class ArrowsShowTheDirectionOfTheWalk(Model):
    """Writes the arrow of the walk, not of the stored fact: forward for a step away, always."""

    def arrow(self, node: str, fact: Fact) -> tuple[str, str]:
        subject, relation, obj = fact
        other = obj if node == subject else subject
        return f" <-{relation}- {other}", other


class SelfLoopWrittenBackwards(Model):
    """Writes a fact about one entity with the backward arrow."""

    def arrow(self, node: str, fact: Fact) -> tuple[str, str]:
        subject, relation, obj = fact
        if subject == obj:
            return f" <-{relation}- {subject}", subject
        return super().arrow(node, fact)


class HeaderCountsTheBudgetAsUsed(Model):
    """Writes the budget where the used tokens go."""

    def header(self, entity: str, chosen: int, used: int, budget: int) -> str:
        return super().header(entity, chosen, budget, budget)


class HeaderCountsAllRankedFacts(Model):
    """Counts the facts of the ranking and not those chosen."""

    def render_context(self, entity: str, hops: int, now: int, half_life: int, budget: int) -> str:
        text = super().render_context(entity, hops, now, half_life, budget)
        total = len(self.ranked(entity, hops, now, half_life))
        return re.sub(r"\((\d+) facts", f"({total} facts", text, count=1)


class HeaderSaysFactForOne(Model):
    """Writes the singular for one fact."""

    def header(self, entity: str, chosen: int, used: int, budget: int) -> str:
        text = super().header(entity, chosen, used, budget)
        return text.replace("(1 facts", "(1 fact")


class NumberingFromZero(Model):
    """Numbers the facts from 0."""

    def numbering_start(self) -> int:
        return 0


class TextEndsWithANewline(Model):
    """Adds a newline at the end."""

    def closing(self) -> str:
        return "\n"


class BudgetAlsoPaysForThePath(Model):
    """Counts the tokens of the path text against the budget."""

    def fits(self, tokens: int, remaining: int) -> bool:
        return tokens + 2 <= remaining


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
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError, StopIteration):
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


def test_a_hidden_case_asks_for_the_deepest_network_and_the_largest_score():
    asked = [
        arguments
        for case in HIDDEN_CASES
        for op, arguments in zip(case["ops"], case["args"], strict=True)
        if op == "egoNetwork"
    ]
    assert any(arguments[1] == 5 for arguments in asked)
    scores = [
        int(row[4])
        for case in HIDDEN_CASES
        for op, rows in zip(case["ops"], case["expected"], strict=True)
        if op == "rankFacts"
        for row in rows
    ]
    assert max(scores) == 100 * 16 * 16
