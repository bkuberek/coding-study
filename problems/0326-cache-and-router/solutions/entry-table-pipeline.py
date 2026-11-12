import re
from dataclasses import dataclass
from fractions import Fraction
from math import isqrt

CHARACTERS_PER_TOKEN = 4
PERMILLE = 1000
PERMILLE_SQUARED = PERMILLE * PERMILLE
NO_SOURCE_VERSION = 0
BLANK = " \t\n"


def normalize(prompt: str) -> str:
    """Trim, collapse each run of spaces, tabs and newlines to one space, lowercase ASCII."""
    return " ".join(re.split(r"[ \t\n]+", prompt.strip(BLANK))).lower()


def token_count(text: str) -> int:
    """The characters of the text in groups of 4, rounded up."""
    return -(-len(text) // CHARACTERS_PER_TOKEN)


def floor_percent(part: int, whole: int) -> int:
    return 100 * part // whole if whole > 0 else 0


@dataclass
class _Entry:
    key: str
    response: str
    embedding: tuple[int, ...] | None
    source: str
    version: int
    sequence: int


@dataclass
class _Tier:
    calls: int = 0
    full_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    cost: int = 0


class CacheRouter:
    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}
        self._next_sequence = 0
        self._source_versions: dict[str, int] = {}
        self._exact_hits = 0
        self._semantic_hits = 0
        self._misses = 0
        self._limits: list[int] = []
        self._label_tiers: dict[str, int] = {}
        self._markers: list[str] = []
        self._prices: tuple[list[int], list[int], list[int]] = ([], [], [])
        self._prefix_tokens: dict[str, int] = {}
        self._threshold = PERMILLE
        self._warm: list[set[str]] = []
        self._tiers: list[_Tier] = []
        self._requests = 0
        self._total_cost = 0
        self._total_baseline = 0

    # Level 1
    def key(self, prompt: str) -> str:
        return normalize(prompt)

    def put(self, prompt: str, response: str) -> bool:
        return self._insert(normalize(prompt), response, None, "")

    def lookup(self, prompt: str) -> list[str]:
        entry = self._entries.get(normalize(prompt))
        if entry is None:
            self._misses += 1
            return ["miss"]
        self._exact_hits += 1
        return ["hit", entry.response]

    def stats(self) -> list[int]:
        hits = self._exact_hits + self._semantic_hits
        percent = floor_percent(hits, hits + self._misses)
        return [hits, self._misses, len(self._entries), percent]

    # Level 2
    def put_semantic(self, prompt: str, embedding: list[int], response: str, source: str) -> bool:
        return self._insert(normalize(prompt), response, tuple(embedding), source)

    def lookup_semantic(self, prompt: str, embedding: list[int], threshold: int) -> list[str]:
        entry = self._entries.get(normalize(prompt))
        if entry is not None:
            self._exact_hits += 1
            return ["hit", "exact", entry.response]
        best = self._nearest(tuple(embedding), threshold)
        if best is None:
            self._misses += 1
            return ["miss"]
        self._semantic_hits += 1
        entry, permille = best
        return ["hit", "semantic", entry.response, entry.key, str(permille)]

    def set_source_version(self, source: str, version: int) -> int:
        self._source_versions[source] = version
        stale = [
            key
            for key, entry in self._entries.items()
            if entry.source == source and entry.version != version
        ]
        for key in stale:
            del self._entries[key]
        return len(stale)

    # Level 3
    def configure_routing(
        self,
        tier_limits: list[int],
        labels: list[str],
        label_tiers: list[int],
        invalid_markers: list[str],
    ) -> None:
        self._limits = list(tier_limits)
        self._label_tiers = dict(zip(labels, label_tiers, strict=True))
        self._markers = list(invalid_markers)
        self._warm = [set() for _ in self._limits]
        self._tiers = [_Tier() for _ in self._limits]

    def route(self, label: str, prompt_tokens: int) -> int:
        start = self._label_tiers.get(label, len(self._limits) - 1)
        for tier in range(start, len(self._limits)):
            if prompt_tokens <= self._limits[tier]:
                return tier
        return -1

    def answer(self, label: str, prompt_tokens: int, answers: list[str]) -> list[str]:
        status, called, text = self._attempt(label, prompt_tokens, answers)
        return [status, ">".join(str(tier) for tier in called), text]

    # Level 4
    def set_prices(
        self, input_prices: list[int], output_prices: list[int], cached_prices: list[int]
    ) -> None:
        self._prices = (list(input_prices), list(output_prices), list(cached_prices))

    def define_prefix(self, prefix_id: str, tokens: int) -> None:
        self._prefix_tokens[prefix_id] = tokens

    def set_threshold(self, threshold: int) -> None:
        self._threshold = threshold

    def handle(
        self,
        prompt: str,
        embedding: list[int],
        label: str,
        source: str,
        answers: list[str],
        prefix_id: str,
    ) -> list[str]:
        tokens = token_count(prompt)
        hit = self.lookup_semantic(prompt, embedding, self._threshold)
        if hit[0] == "hit":
            status, called, text, cost = hit[1], [], hit[2], 0
        else:
            status, called, text = self._attempt(label, tokens, answers)
            cost = sum(self._bill(tier, tokens, answers[tier], prefix_id) for tier in called)
            if status in ("ok", "escalated"):
                self.put_semantic(prompt, embedding, text, source)
        baseline = self._baseline(tokens, answers)
        self._requests += 1
        self._total_cost += cost
        self._total_baseline += baseline
        calls = ">".join(str(tier) for tier in called)
        return [status, calls, text, str(cost), str(baseline)]

    def report(self) -> list[list[str]]:
        savings = self._total_baseline - self._total_cost
        percent = floor_percent(savings, self._total_baseline)
        rows = [
            ["total", str(self._requests), str(self._total_cost), str(self._total_baseline)]
            + [str(savings), str(percent)],
            ["cache", str(self._exact_hits), str(self._semantic_hits), str(self._misses)],
        ]
        for index, tier in enumerate(self._tiers):
            rows.append(
                ["tier", str(index), str(tier.calls), str(tier.full_tokens)]
                + [str(tier.cached_tokens), str(tier.output_tokens), str(tier.cost)]
            )
        return rows

    # Helpers
    def _insert(
        self, key: str, response: str, embedding: tuple[int, ...] | None, source: str
    ) -> bool:
        if key in self._entries:
            return False
        version = self._source_versions.get(source, NO_SOURCE_VERSION) if source else 0
        self._entries[key] = _Entry(key, response, embedding, source, version, self._next_sequence)
        self._next_sequence += 1
        return True

    def _nearest(
        self, query: tuple[int, ...], threshold: int
    ) -> tuple[_Entry, int] | None:
        query_norm = sum(x * x for x in query)
        best: tuple[Fraction, int, _Entry, int] | None = None
        for entry in self._entries.values():
            if entry.embedding is None or query_norm == 0:
                continue
            dot = sum(x * y for x, y in zip(query, entry.embedding, strict=True))
            norm = sum(y * y for y in entry.embedding)
            if dot <= 0 or norm == 0:
                continue
            permille = isqrt(PERMILLE_SQUARED * dot * dot // (query_norm * norm))
            if permille < threshold:
                continue
            closeness = Fraction(dot * dot, norm)
            if best is None or (closeness, -entry.sequence) > (best[0], -best[1]):
                best = (closeness, entry.sequence, entry, permille)
        return None if best is None else (best[2], best[3])

    def _is_valid(self, text: str) -> bool:
        return text.strip(BLANK) != "" and not any(marker in text for marker in self._markers)

    def _attempt(
        self, label: str, prompt_tokens: int, answers: list[str]
    ) -> tuple[str, list[int], str]:
        tier = self.route(label, prompt_tokens)
        if tier < 0:
            return "too_long", [], ""
        if self._is_valid(answers[tier]):
            return "ok", [tier], answers[tier]
        if tier == len(self._limits) - 1:
            return "invalid", [tier], answers[tier]
        higher = answers[tier + 1]
        status = "escalated" if self._is_valid(higher) else "invalid"
        return status, [tier, tier + 1], higher

    def _bill(self, tier: int, tokens: int, answer: str, prefix_id: str) -> int:
        input_price, output_price, cached_price = (prices[tier] for prices in self._prices)
        reused = prefix_id != "" and prefix_id in self._warm[tier]
        cached = min(self._prefix_tokens.get(prefix_id, 0), tokens) if reused else 0
        output = token_count(answer)
        cost = (tokens - cached) * input_price + cached * cached_price + output * output_price
        if prefix_id != "":
            self._warm[tier].add(prefix_id)
        ledger = self._tiers[tier]
        ledger.calls += 1
        ledger.full_tokens += tokens - cached
        ledger.cached_tokens += cached
        ledger.output_tokens += output
        ledger.cost += cost
        return cost

    def _baseline(self, tokens: int, answers: list[str]) -> int:
        if tokens > self._limits[-1]:
            return 0
        return tokens * self._prices[0][-1] + token_count(answers[-1]) * self._prices[1][-1]
