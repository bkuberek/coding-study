"""cache-and-router promises that its hidden cases catch the classic mistakes of a cache and a
router in front of language models: a key that keeps what it should drop or drops what it should
keep, a duplicate that overwrites, a percent that rounds the wrong way, a similarity worked out in
floating point or ranked by its rounded value, a tie that goes to the wrong entry, an exact key that
is tried second, a version that retires too many or too few entries, a threshold that is read as
strict, a label that is ignored or an unknown label that is trusted, an escalation that happens
twice or jumps to the top, a check that lets a blank or a marked answer through, a prefix that is
discounted too early or too widely, a call that is not paid for, a bad answer that is cached, and a
percent that is rounded toward zero. These tests replay every case against a model of the gateway
written from the statement, which must give every expected output, and against that model with one
mistake planted at a time, which some hidden case must fail. A mistake that crashes fails its case,
as a thrown exception does in the grader."""

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0326-cache-and-router"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

BLANK = " \t\n"
SCALE = 10**6
PERMILLE = 1000


@dataclass
class Row:
    key: str
    raw: str
    response: str
    embedding: tuple[int, ...] | None
    source: str
    version: int
    order: int


class Model:
    """The gateway as the statement words it. The entries are a list and every answer is found by
    looking at all of them, so each mistake below overrides a single rule."""

    def __init__(self) -> None:
        self.table: list[Row] = []
        self.counter = 0
        self.versions: dict[str, int] = {}
        self.exact = 0
        self.semantic = 0
        self.misses = 0
        self.limits: list[int] = []
        self.start: dict[str, int] = {}
        self.markers: list[str] = []
        self.prices: tuple[list[int], list[int], list[int]] = ([], [], [])
        self.prefix_length: dict[str, int] = {}
        self.warm: set[tuple[int, str]] = set()
        self.threshold = PERMILLE
        self.requests = 0
        self.total_cost = 0
        self.total_baseline = 0
        self.tiers: list[list[int]] = []

    # --- level 1
    def trim(self, text: str) -> str:
        return text.strip(BLANK)

    def collapse(self, text: str) -> str:
        return re.sub(r"[ \t\n]+", " ", text)

    def fold(self, text: str) -> str:
        return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in text)

    def key(self, prompt: str) -> str:
        return self.fold(self.collapse(self.trim(prompt)))

    def lookup_key(self, prompt: str) -> str:
        return self.key(prompt)

    def find(self, key: str) -> Row | None:
        return next((row for row in self.table if row.key == key), None)

    def version_for_new(self, source: str) -> int:
        return self.versions.get(source, 0)

    def on_duplicate(self, old: Row, response: str, embedding: Any, source: str) -> bool:
        return False

    def add(
        self, prompt: str, response: str, embedding: tuple[int, ...] | None, source: str
    ) -> bool:
        key = self.key(prompt)
        old = self.find(key)
        if old is not None:
            return self.on_duplicate(old, response, embedding, source)
        self.counter += 1
        row = Row(
            key, prompt, response, embedding, source, self.version_for_new(source), self.counter
        )
        self.table.append(row)
        return True

    def put(self, prompt: str, response: str) -> bool:
        return self.add(prompt, response, None, "")

    def count_miss(self) -> None:
        self.misses += 1

    def count_exact(self) -> None:
        self.exact += 1

    def count_semantic(self) -> None:
        self.semantic += 1

    def lookup(self, prompt: str) -> list[str]:
        row = self.find(self.lookup_key(prompt))
        if row is None:
            self.count_miss()
            return ["miss"]
        self.count_exact()
        return ["hit", row.response]

    def hit_total(self) -> int:
        return self.exact + self.semantic

    def percent(self, hits: int, total: int) -> int:
        return 100 * hits // total if total else 0

    def entry_count(self) -> int:
        return len(self.table)

    def stats(self) -> list[int]:
        hits = self.hit_total()
        return [hits, self.misses, self.entry_count(), self.percent(hits, hits + self.misses)]

    # --- level 2
    def put_semantic(self, prompt: str, embedding: list[int], response: str, source: str) -> bool:
        return self.add(prompt, response, tuple(embedding), source)

    def similarity(self, query: Sequence[int], other: Sequence[int]) -> tuple[int, int, int] | None:
        dot = sum(a * b for a, b in zip(query, other, strict=True))
        nq = sum(a * a for a in query)
        nd = sum(b * b for b in other)
        if dot <= 0 or nq == 0 or nd == 0:
            return None
        return dot, nq, nd

    def permille(self, dot: int, nq: int, nd: int) -> int:
        top, bottom = SCALE * dot * dot, nq * nd
        return max(p for p in range(PERMILLE + 1) if p * p * bottom <= top)

    def passes(self, permille: int, threshold: int) -> bool:
        return permille >= threshold

    def better(self, new: tuple[Row, int, int, int], held: tuple[Row, int, int, int]) -> bool:
        return new[2] ** 2 * held[3] > held[2] ** 2 * new[3]

    def reported_key(self, row: Row, prompt: str) -> str:
        return row.key

    def steps(self) -> list[str]:
        return ["exact", "semantic"]

    def exact_allowed(self, row: Row) -> bool:
        return True

    def try_exact(self, prompt: str) -> list[str] | None:
        row = self.find(self.key(prompt))
        if row is None or not self.exact_allowed(row):
            return None
        self.count_exact()
        return ["hit", "exact", row.response]

    def candidates(
        self, embedding: Sequence[int], threshold: int
    ) -> list[tuple[Row, int, int, int]]:
        found = []
        for row in self.table:
            if row.embedding is None:
                continue
            numbers = self.similarity(embedding, row.embedding)
            if numbers is None:
                continue
            permille = self.permille(*numbers)
            if self.passes(permille, threshold):
                found.append((row, permille, numbers[0], numbers[2]))
        return found

    def try_semantic(self, prompt: str, embedding: list[int], threshold: int) -> list[str] | None:
        best = None
        for item in self.candidates(embedding, threshold):
            if best is None or self.better(item, best):
                best = item
        if best is None:
            return None
        self.count_semantic()
        return [
            "hit",
            "semantic",
            best[0].response,
            self.reported_key(best[0], prompt),
            str(best[1]),
        ]

    def lookup_semantic(self, prompt: str, embedding: list[int], threshold: int) -> list[str]:
        for step in self.steps():
            found = (
                self.try_exact(prompt)
                if step == "exact"
                else self.try_semantic(prompt, embedding, threshold)
            )
            if found is not None:
                return found
        self.count_miss()
        return ["miss"]

    def remember_version(self, source: str, version: int) -> None:
        self.versions[source] = version

    def retires(self, row: Row, source: str, version: int) -> bool:
        return row.source == source and row.version != version

    def removed_count(self, removed: list[Row]) -> int:
        return len(removed)

    def set_source_version(self, source: str, version: int) -> int:
        self.remember_version(source, version)
        removed = [row for row in self.table if self.retires(row, source, version)]
        self.table = [row for row in self.table if row not in removed]
        return self.removed_count(removed)

    # --- level 3
    def configure_routing(
        self, limits: list[int], labels: list[str], label_tiers: list[int], markers: list[str]
    ) -> None:
        self.limits = list(limits)
        self.start = dict(zip(labels, label_tiers, strict=True))
        self.markers = list(markers)
        self.warm = set()
        self.tiers = [[0, 0, 0, 0, 0] for _ in limits]

    def start_tier(self, label: str) -> int:
        return self.start.get(label, len(self.limits) - 1)

    def fits(self, tokens: int, tier: int) -> bool:
        return tokens <= self.limits[tier]

    def route(self, label: str, prompt_tokens: int) -> int:
        for tier in range(self.start_tier(label), len(self.limits)):
            if self.fits(prompt_tokens, tier):
                return tier
        return -1

    def not_blank(self, text: str) -> bool:
        return text.strip(BLANK) != ""

    def has_marker(self, text: str) -> bool:
        return any(marker in text for marker in self.markers)

    def valid(self, text: str) -> bool:
        return self.not_blank(text) and not self.has_marker(text)

    def next_tier(self, tier: int, label: str) -> int | None:
        return tier + 1 if tier + 1 < len(self.limits) else None

    def result_text(self, text: str) -> str:
        return text

    def attempt(self, label: str, tokens: int, answers: list[str]) -> tuple[str, list[int], str]:
        tier = self.route(label, tokens)
        if tier < 0:
            return "too_long", [], ""
        first = answers[tier]
        if self.valid(first):
            return "ok", [tier], self.result_text(first)
        higher = self.next_tier(tier, label)
        if higher is None:
            return "invalid", [tier], self.result_text(first)
        second = answers[higher]
        status = "escalated" if self.valid(second) else "invalid"
        return status, [tier, higher], self.result_text(second)

    def joiner(self) -> str:
        return ">"

    def answer(self, label: str, prompt_tokens: int, answers: list[str]) -> list[str]:
        status, calls, text = self.attempt(label, prompt_tokens, answers)
        return [status, self.joiner().join(str(tier) for tier in calls), text]

    # --- level 4
    def set_prices(self, inputs: list[int], outputs: list[int], cached: list[int]) -> None:
        self.prices = (list(inputs), list(outputs), list(cached))

    def define_prefix(self, prefix_id: str, tokens: int) -> None:
        self.prefix_length[prefix_id] = tokens

    def set_threshold(self, threshold: int) -> None:
        self.threshold = threshold

    def tokens(self, text: str) -> int:
        return -(-len(text) // 4)

    def prompt_tokens(self, prompt: str) -> int:
        return self.tokens(prompt)

    def output_tokens(self, text: str) -> int:
        return self.tokens(text)

    def warm_key(self, tier: int, prefix_id: str) -> tuple[int, str]:
        return (tier, prefix_id)

    def reused(self, tier: int, tokens: int, prefix_id: str) -> int:
        if prefix_id == "" or self.warm_key(tier, prefix_id) not in self.warm:
            return 0
        return min(self.prefix_length.get(prefix_id, 0), tokens)

    def mark_warm(self, tier: int, prefix_id: str, valid: bool) -> None:
        if prefix_id != "":
            self.warm.add(self.warm_key(tier, prefix_id))

    def bill(self, tier: int, tokens: int, text: str, prefix_id: str) -> int:
        prices = [column[tier] for column in self.prices]
        reused = self.reused(tier, tokens, prefix_id)
        out = self.output_tokens(text)
        cost = (tokens - reused) * prices[0] + reused * prices[2] + out * prices[1]
        row = self.tiers[tier]
        row[0] += 1
        row[1] += tokens - reused
        row[2] += reused
        row[3] += out
        row[4] += cost
        self.mark_warm(tier, prefix_id, self.valid(text))
        return cost

    def billed_calls(self, calls: list[int]) -> list[int]:
        return calls

    def pay(self, calls: list[int], tokens: int, answers: list[str], prefix_id: str) -> int:
        return sum(
            self.bill(tier, tokens, answers[tier], prefix_id) for tier in self.billed_calls(calls)
        )

    def hit_cost(self, tokens: int) -> int:
        return 0

    def storable(self, status: str) -> bool:
        return status in ("ok", "escalated")

    def stored_source(self, source: str) -> str:
        return source

    def baseline(self, status: str, tokens: int, answers: list[str], calls: list[int]) -> int:
        if tokens > self.limits[-1]:
            return 0
        return tokens * self.prices[0][-1] + self.tokens(answers[-1]) * self.prices[1][-1]

    def counted_as_request(self, status: str) -> bool:
        return True

    def savings_percent(self, savings: int, baseline: int, cost: int) -> int:
        return 100 * savings // baseline if baseline else 0

    def handle(
        self,
        prompt: str,
        embedding: list[int],
        label: str,
        source: str,
        answers: list[str],
        prefix_id: str,
    ) -> list[str]:
        tokens = self.prompt_tokens(prompt)
        hit = self.lookup_semantic(prompt, embedding, self.threshold)
        if hit[0] == "hit":
            status, calls, text, cost = hit[1], [], hit[2], self.hit_cost(tokens)
        else:
            status, calls, text = self.attempt(label, tokens, answers)
            cost = self.pay(calls, tokens, answers, prefix_id)
            if self.storable(status):
                self.put_semantic(prompt, embedding, text, self.stored_source(source))
        baseline = self.baseline(status, tokens, answers, calls)
        if self.counted_as_request(status):
            self.requests += 1
        self.total_cost += cost
        self.total_baseline += baseline
        joined = self.joiner().join(str(tier) for tier in calls)
        return [status, joined, text, str(cost), str(baseline)]

    def report(self) -> list[list[str]]:
        savings = self.total_baseline - self.total_cost
        percent = self.savings_percent(savings, self.total_baseline, self.total_cost)
        rows = [
            [
                "total",
                str(self.requests),
                str(self.total_cost),
                str(self.total_baseline),
                str(savings),
                str(percent),
            ],
            ["cache", str(self.exact), str(self.semantic), str(self.misses)],
        ]
        for index, row in enumerate(self.tiers):
            rows.append(["tier", str(index), *(str(number) for number in row)])
        return rows


# ------------------------------------------------------------------ level 1 mistakes
class KeyKeepsCapitals(Model):
    """Leaves the letters as typed."""

    def fold(self, text: str) -> str:
        return text


class KeyKeepsOuterWhitespace(Model):
    """Trims nothing, so the ends become one space each."""

    def trim(self, text: str) -> str:
        return text


class KeyCollapsesOnlySpaces(Model):
    """Collapses runs of spaces, and leaves tabs and newlines as they are."""

    def collapse(self, text: str) -> str:
        return re.sub(r" +", " ", text)


class KeyRemovesAllWhitespace(Model):
    """Squeezes the words together."""

    def collapse(self, text: str) -> str:
        return re.sub(r"[ \t\n]+", "", text)


class KeyDropsPunctuation(Model):
    """Keeps only letters, digits and spaces."""

    def fold(self, text: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", super().fold(text))


class KeyDropsTrailingQuestionMark(Model):
    """Treats a closing question mark as part of the layout."""

    def trim(self, text: str) -> str:
        return text.strip(BLANK).rstrip("?")


class LookupSkipsTheInnerCollapse(Model):
    """Normalises what is stored and not what is asked."""

    def lookup_key(self, prompt: str) -> str:
        return self.fold(self.trim(prompt))


class DuplicatePutOverwrites(Model):
    """Replaces the response of a key that is stored, and says it was not new."""

    def on_duplicate(self, old: Row, response: str, embedding: Any, source: str) -> bool:
        old.response = response
        return False


class DuplicatePutSaysTrue(Model):
    """Keeps the first response and still answers true."""

    def on_duplicate(self, old: Row, response: str, embedding: Any, source: str) -> bool:
        return True


class PercentRoundsToNearest(Model):
    """Rounds the share of hits to the nearest whole percent."""

    def percent(self, hits: int, total: int) -> int:
        return (200 * hits + total) // (2 * total) if total else 0


class PercentOfNothingIsAHundred(Model):
    """Says every lookup hit when there has been none."""

    def percent(self, hits: int, total: int) -> int:
        return 100 * hits // total if total else 100


class MissesAreNotCounted(Model):
    """Counts the hits only."""

    def count_miss(self) -> None:
        return None


class HitsAreNotCounted(Model):
    """Counts the misses only."""

    def count_exact(self) -> None:
        return None


class EntriesCountsEveryPut(Model):
    """Counts the calls of put and not the keys."""

    def __init__(self) -> None:
        super().__init__()
        self.puts = 0

    def add(
        self, prompt: str, response: str, embedding: tuple[int, ...] | None, source: str
    ) -> bool:
        self.puts += 1
        return super().add(prompt, response, embedding, source)

    def entry_count(self) -> int:
        return self.puts


class MissStoresAnEmptyEntry(Model):
    """Writes a placeholder for a key that was asked and not found."""

    def lookup(self, prompt: str) -> list[str]:
        found = super().lookup(prompt)
        if found == ["miss"]:
            self.table.append(Row(self.key(prompt), prompt, "", None, "", 0, 10**9))
        return found


# ------------------------------------------------------------------ level 2 mistakes
class SemanticIsTriedFirst(Model):
    """Looks for a similar entry before looking for the same key."""

    def steps(self) -> list[str]:
        return ["semantic", "exact"]


class ExactNeedsAnEmbedding(Model):
    """Finds an entry through its key only when it was stored with an embedding."""

    def exact_allowed(self, row: Row) -> bool:
        return row.embedding is not None


class SimilarityInFloatingPoint(Model):
    """Works out the cosine with decimals and rounds down."""

    def permille(self, dot: int, nq: int, nd: int) -> int:
        return int(PERMILLE * dot / (math.sqrt(nq) * math.sqrt(nd)))


class ThresholdIsStrict(Model):
    """Needs more than the threshold."""

    def passes(self, permille: int, threshold: int) -> bool:
        return permille > threshold


class PermilleRoundedToNearest(Model):
    """Rounds the similarity to the nearest permille."""

    def permille(self, dot: int, nq: int, nd: int) -> int:
        top, bottom = SCALE * dot * dot, nq * nd
        steps = [p for p in range(1, PERMILLE + 1) if (2 * p - 1) ** 2 * bottom <= 4 * top]
        return max(steps, default=0)


class TieGoesToTheLastStored(Model):
    """Lets a later entry take an equal similarity."""

    def better(self, new: tuple[Row, int, int, int], held: tuple[Row, int, int, int]) -> bool:
        return new[2] ** 2 * held[3] >= held[2] ** 2 * new[3]


class TieGoesToTheSmallerKey(Model):
    """Breaks an equal similarity by the key."""

    def better(self, new: tuple[Row, int, int, int], held: tuple[Row, int, int, int]) -> bool:
        left, right = new[2] ** 2 * held[3], held[2] ** 2 * new[3]
        return left > right or (left == right and new[0].key < held[0].key)


class RanksByTheRoundedPermille(Model):
    """Compares the permille, so entries that round alike tie."""

    def better(self, new: tuple[Row, int, int, int], held: tuple[Row, int, int, int]) -> bool:
        return new[1] > held[1]


class SimilarityIgnoresTheSign(Model):
    """Uses the size of the dot product, so an opposite direction matches."""

    def similarity(self, query: Sequence[int], other: Sequence[int]) -> tuple[int, int, int] | None:
        dot = sum(a * b for a, b in zip(query, other, strict=True))
        nq = sum(a * a for a in query)
        nd = sum(b * b for b in other)
        if dot == 0 or nq == 0 or nd == 0:
            return None
        return abs(dot), nq, nd


class SimilarityIgnoresLength(Model):
    """Is the dot product with no division by the lengths, capped at a thousand."""

    def permille(self, dot: int, nq: int, nd: int) -> int:
        return min(PERMILLE, dot)


class ZeroEntryMatchesEverything(Model):
    """Gives an entry with no direction the best similarity."""

    def similarity(self, query: Sequence[int], other: Sequence[int]) -> tuple[int, int, int] | None:
        if not any(other) and any(query):
            return 1, 1, 1
        return super().similarity(query, other)


class HitReportsTheQueryKey(Model):
    """Shows the key of the question and not of the entry."""

    def reported_key(self, row: Row, prompt: str) -> str:
        return self.key(prompt)


class HitReportsTheTextAsWritten(Model):
    """Shows the prompt of the entry as it was first typed."""

    def reported_key(self, row: Row, prompt: str) -> str:
        return row.raw


class SemanticHitStoresTheQuestion(Model):
    """Adds the new question as an entry that points at the same response."""

    def lookup_semantic(self, prompt: str, embedding: list[int], threshold: int) -> list[str]:
        found = super().lookup_semantic(prompt, embedding, threshold)
        if found[:2] == ["hit", "semantic"]:
            self.put_semantic(prompt, embedding, found[2], "")
        return found


class SemanticHitsAreNotHits(Model):
    """Counts the hits of an exact key only."""

    def count_semantic(self) -> None:
        return None

    def hit_total(self) -> int:
        return self.exact


class RetiresOnlyOlderVersions(Model):
    """Leaves an entry of a newer version in place."""

    def retires(self, row: Row, source: str, version: int) -> bool:
        return row.source == source and row.version < version


class RetiresEveryone(Model):
    """Clears the whole table whatever the source."""

    def retires(self, row: Row, source: str, version: int) -> bool:
        return row.version != version


class RetiresEntriesWithoutASource(Model):
    """Drops the entries of put as well."""

    def retires(self, row: Row, source: str, version: int) -> bool:
        return (row.source == source or row.source == "") and row.version != version


class RetiresTheCurrentVersionToo(Model):
    """Removes the entries of the very version that is being set."""

    def retires(self, row: Row, source: str, version: int) -> bool:
        return row.source == source and row.version <= version


class NewEntriesAlwaysCarryVersionZero(Model):
    """Forgets the version when storing."""

    def version_for_new(self, source: str) -> int:
        return 0


class VersionIsNotRemembered(Model):
    """Removes what is stale and leaves the source at its old version."""

    def remember_version(self, source: str, version: int) -> None:
        return None


class RemovedCountIsWhatIsLeft(Model):
    """Returns the size of the table after the removal."""

    def removed_count(self, removed: list[Row]) -> int:
        return len(self.table)


class SemanticPutOverwritesAKey(Model):
    """Lets putSemantic replace an entry that is stored, and say it was new."""

    def on_duplicate(self, old: Row, response: str, embedding: Any, source: str) -> bool:
        if embedding is None:
            return False
        old.response, old.embedding, old.source = response, embedding, source
        return True


# ------------------------------------------------------------------ level 3 mistakes
class LengthRuleIsIgnored(Model):
    """Starts at the tier of the label and stays there."""

    def route(self, label: str, prompt_tokens: int) -> int:
        tier = self.start_tier(label)
        return tier if prompt_tokens <= self.limits[-1] else -1


class LimitIsExclusive(Model):
    """Needs the prompt to be shorter than the limit."""

    def fits(self, tokens: int, tier: int) -> bool:
        return tokens < self.limits[tier]


class UnknownLabelStartsAtTheCheapestTier(Model):
    """Trusts a label it does not know."""

    def start_tier(self, label: str) -> int:
        return self.start.get(label, 0)


class UnknownLabelHasNoRoute(Model):
    """Refuses a label it does not know."""

    def route(self, label: str, prompt_tokens: int) -> int:
        return -1 if label not in self.start else super().route(label, prompt_tokens)


class CheapestTierThatFits(Model):
    """Ignores the label and takes the first tier the prompt fits."""

    def start_tier(self, label: str) -> int:
        return 0


class EscalatesUntilValid(Model):
    """Climbs the ladder as long as the answers are not valid."""

    def attempt(self, label: str, tokens: int, answers: list[str]) -> tuple[str, list[int], str]:
        tier = self.route(label, tokens)
        if tier < 0:
            return "too_long", [], ""
        calls = [tier]
        while not self.valid(answers[calls[-1]]) and calls[-1] + 1 < len(self.limits):
            calls.append(calls[-1] + 1)
        text = answers[calls[-1]]
        if not self.valid(text):
            return "invalid", calls, text
        return ("ok" if len(calls) == 1 else "escalated"), calls, text


class EscalatesStraightToTheTop(Model):
    """Skips the tiers in between."""

    def next_tier(self, tier: int, label: str) -> int | None:
        return len(self.limits) - 1 if tier < len(self.limits) - 1 else None


class EscalatesFromTheLabelTier(Model):
    """Goes one above the tier the label names, not the tier that was used."""

    def next_tier(self, tier: int, label: str) -> int | None:
        higher = self.start_tier(label) + 1
        return higher if higher < len(self.limits) else None


class FailedEscalationReturnsTheFirstAnswer(Model):
    """Keeps the cheap answer when the dear one is not valid either."""

    def attempt(self, label: str, tokens: int, answers: list[str]) -> tuple[str, list[int], str]:
        status, calls, text = super().attempt(label, tokens, answers)
        if status == "invalid" and len(calls) == 2:
            return status, calls, answers[calls[0]]
        return status, calls, text


class BlankAnswerIsValid(Model):
    """Looks only for markers."""

    def not_blank(self, text: str) -> bool:
        return True


class SpacesOnlyIsBlank(Model):
    """Counts only spaces as blank, so a tab or a newline passes."""

    def not_blank(self, text: str) -> bool:
        return text.strip(" ") != ""


class MarkersIgnoreCapitals(Model):
    """Compares the marker and the answer in lowercase."""

    def has_marker(self, text: str) -> bool:
        return any(marker.lower() in text.lower() for marker in self.markers)


class MarkerMustOpenTheAnswer(Model):
    """Looks for a marker at the start of the answer only."""

    def has_marker(self, text: str) -> bool:
        return any(text.lstrip(BLANK).startswith(marker) for marker in self.markers)


class MarkerMustBeAWholeWord(Model):
    """Looks for a marker between word boundaries."""

    def has_marker(self, text: str) -> bool:
        return any(re.search(rf"\b{re.escape(marker)}\b", text) for marker in self.markers)


class ResultIsTrimmed(Model):
    """Hands back the answer without its outer spaces."""

    def result_text(self, text: str) -> str:
        return text.strip(BLANK)


class CallsAreJoinedWithAComma(Model):
    """Writes the calls as 0,1."""

    def joiner(self) -> str:
        return ","


# ------------------------------------------------------------------ level 4 mistakes
class PrefixIsDiscountedOnFirstUse(Model):
    """Gives the cached price before the prefix has been paid for."""

    def reused(self, tier: int, tokens: int, prefix_id: str) -> int:
        if prefix_id == "":
            return 0
        return min(self.prefix_length.get(prefix_id, 0), tokens)


class PrefixIsWarmInEveryTier(Model):
    """Shares the memory of the prefix between tiers."""

    def warm_key(self, tier: int, prefix_id: str) -> tuple[int, str]:
        return (0, prefix_id)


class PrefixIsNotCappedByThePrompt(Model):
    """Bills the whole prefix even when the prompt is shorter."""

    def reused(self, tier: int, tokens: int, prefix_id: str) -> int:
        if prefix_id == "" or self.warm_key(tier, prefix_id) not in self.warm:
            return 0
        return self.prefix_length.get(prefix_id, 0)


class WholePromptIsCachedWhenWarm(Model):
    """Bills every input token at the cached price once the prefix is warm."""

    def reused(self, tier: int, tokens: int, prefix_id: str) -> int:
        if super().reused(tier, tokens, prefix_id) > 0:
            return tokens
        return 0


class OnlyTheLastCallIsPaid(Model):
    """Pays for the answer that was returned and not for the cheap try."""

    def billed_calls(self, calls: list[int]) -> list[int]:
        return calls[-1:]


class OnlyTheFirstCallIsPaid(Model):
    """Pays for the first call and not for the escalation."""

    def billed_calls(self, calls: list[int]) -> list[int]:
        return calls[:1]


class InvalidAnswerIsNotPaid(Model):
    """Does not charge the output of an answer that failed the check."""

    def output_tokens(self, text: str) -> int:
        return super().output_tokens(text) if self.valid(text) else 0


class HitPaysTheCheapestInput(Model):
    """Charges the lookup as an input at the first tier."""

    def hit_cost(self, tokens: int) -> int:
        return tokens * self.prices[0][0]


class BaselineUsesTheTierThatAnswered(Model):
    """Prices the baseline at the last tier that was called, when there was a call."""

    def baseline(self, status: str, tokens: int, answers: list[str], calls: list[int]) -> int:
        if tokens > self.limits[-1]:
            return 0
        tier = calls[-1] if calls else len(self.limits) - 1
        return tokens * self.prices[0][tier] + self.tokens(answers[tier]) * self.prices[1][tier]


class BaselineLeavesOutTheHits(Model):
    """Has no baseline for a request that the cache answered."""

    def baseline(self, status: str, tokens: int, answers: list[str], calls: list[int]) -> int:
        return (
            0
            if status in ("exact", "semantic")
            else super().baseline(status, tokens, answers, calls)
        )


class BaselineOfALongPromptIsNotZero(Model):
    """Prices a prompt that fits no tier."""

    def baseline(self, status: str, tokens: int, answers: list[str], calls: list[int]) -> int:
        return tokens * self.prices[0][-1] + self.tokens(answers[-1]) * self.prices[1][-1]


class InvalidAnswerIsStored(Model):
    """Caches every answer that a call returned."""

    def storable(self, status: str) -> bool:
        return status in ("ok", "escalated", "invalid")


class OnlyAFirstTryAnswerIsStored(Model):
    """Does not cache an answer that needed an escalation."""

    def storable(self, status: str) -> bool:
        return status == "ok"


class StoredWithoutASource(Model):
    """Forgets the source, so a new version cannot retire the answer."""

    def stored_source(self, source: str) -> str:
        return ""


class RequestThatFitsNoTierIsNotCounted(Model):
    """Leaves it out of the number of requests."""

    def counted_as_request(self, status: str) -> bool:
        return status != "too_long"


class TokensComeFromTheKey(Model):
    """Counts the characters of the normal form."""

    def prompt_tokens(self, prompt: str) -> int:
        return self.tokens(self.key(prompt))


class TokensAreRoundedDown(Model):
    """Counts whole groups of 4 characters only."""

    def tokens(self, text: str) -> int:
        return len(text) // 4


class OutputTokensAreWords(Model):
    """Counts one token per word of the answer."""

    def output_tokens(self, text: str) -> int:
        return len(text.split())


class SavingsPercentRoundsToNearest(Model):
    """Rounds the share to the nearest whole percent."""

    def savings_percent(self, savings: int, baseline: int, cost: int) -> int:
        return round(100 * savings / baseline) if baseline else 0


class SavingsPercentRoundsTowardZero(Model):
    """Cuts the decimals off, so -38.2 becomes -38."""

    def savings_percent(self, savings: int, baseline: int, cost: int) -> int:
        return int(100 * savings / baseline) if baseline else 0


class SavingsPercentIsOfTheCost(Model):
    """Divides by what was spent and not by the baseline."""

    def savings_percent(self, savings: int, baseline: int, cost: int) -> int:
        return 100 * savings // cost if cost else 0


class SavingsPercentOfNothingIsAHundred(Model):
    """Says everything was saved when there is no baseline."""

    def savings_percent(self, savings: int, baseline: int, cost: int) -> int:
        return 100 * savings // baseline if baseline else 100


class ThresholdStartsAtOne(Model):
    """Matches anything that points the same way, until a threshold is set."""

    def __init__(self) -> None:
        super().__init__()
        self.threshold = 1


class HitIsCountedAsACall(Model):
    """Adds the calls of a hit to tier 0."""

    def hit_cost(self, tokens: int) -> int:
        self.tiers[0][0] += 1
        return 0


class PrefixIsWarmOnlyAfterAGoodAnswer(Model):
    """Remembers the prefix only when the answer passed the check."""

    def mark_warm(self, tier: int, prefix_id: str, valid: bool) -> None:
        if valid:
            super().mark_warm(tier, prefix_id, valid)


class UnknownPrefixCostsNothing(Model):
    """Treats a prefix that was never defined as the whole prompt, at the cached price."""

    def reused(self, tier: int, tokens: int, prefix_id: str) -> int:
        if (
            prefix_id != ""
            and prefix_id not in self.prefix_length
            and (tier, prefix_id) in self.warm
        ):
            return tokens
        return super().reused(tier, tokens, prefix_id)


class CachedTokensAreAlsoCountedAsFull(Model):
    """Lists the reused tokens in the full column too."""

    def bill(self, tier: int, tokens: int, text: str, prefix_id: str) -> int:
        reused = self.reused(tier, tokens, prefix_id)
        cost = super().bill(tier, tokens, text, prefix_id)
        self.tiers[tier][1] += reused
        return cost


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor and the setters."""
    model = model_type()
    results: list[Any] = [None]
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    for op, arguments in calls:
        results.append(getattr(model, snake_case(op))(*arguments))
    return results


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


def test_a_hidden_case_asks_for_the_boundaries_of_the_threshold_and_of_a_tier():
    asked = [
        arguments
        for case in HIDDEN_CASES
        for op, arguments in zip(case["ops"], case["args"], strict=True)
        if op == "lookupSemantic"
    ]
    assert any(arguments[2] == 1 for arguments in asked)
    assert any(arguments[2] == PERMILLE for arguments in asked)
    limits = [
        (arguments[0], arguments[1])
        for case in HIDDEN_CASES
        for op, arguments in zip(case["ops"], case["args"], strict=True)
        if op == "route"
    ]
    assert any(tokens == 200 for _, tokens in limits)
    assert any(tokens == 201 for _, tokens in limits)


def test_a_hidden_case_ends_with_a_cost_above_the_baseline():
    rows = [
        row
        for case in HIDDEN_CASES
        for op, result in zip(case["ops"], case["expected"], strict=True)
        if op == "report"
        for row in result
        if row[0] == "total"
    ]
    assert any(int(row[4]) < 0 for row in rows)
    assert any(int(row[5]) > 0 for row in rows)
