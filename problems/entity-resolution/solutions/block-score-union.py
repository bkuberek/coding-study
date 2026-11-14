import re
from collections import defaultdict
from itertools import combinations

TITLES = frozenset({"mr", "mrs", "ms", "miss", "dr", "prof"})
NAME_KEY_LENGTH = 3
PREFIX_LIMIT = 4
PREFIX_SCALE = 0.1
JARO_WEIGHT, JACCARD_WEIGHT = 0.7, 0.3
MATCH_THRESHOLD = 0.75
MERGE_FLOOR = 0.65
FALSE_MERGE, MISSED = "false-merge", "missed"


def normalize_name(name: str) -> str:
    text = name.lower()
    if text.count(",") == 1:
        before, after = text.split(",")
        text = after + " " + before
    text = text.replace("'", "")
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    tokens = text.split()
    if len(tokens) > 1 and tokens[0] in TITLES:
        tokens = tokens[1:]
    return " ".join(tokens)


def normalize_email(email: str) -> str:
    return email.strip(" ").lower()


def jaro_winkler(first: str, second: str) -> float:
    if not first or not second:
        return 0.0
    window = max(0, max(len(first), len(second)) // 2 - 1)
    taken = [False] * len(second)
    from_first: list[str] = []
    for i, char in enumerate(first):
        for j in range(max(0, i - window), min(len(second), i + window + 1)):
            if not taken[j] and second[j] == char:
                taken[j] = True
                from_first.append(char)
                break
    matches = len(from_first)
    if matches == 0:
        return 0.0
    from_second = [char for char, used in zip(second, taken, strict=True) if used]
    transpositions = sum(a != b for a, b in zip(from_first, from_second, strict=True)) / 2
    jaro = (
        matches / len(first) + matches / len(second) + (matches - transpositions) / matches
    ) / 3
    prefix = 0
    while prefix < min(PREFIX_LIMIT, len(first), len(second)) and first[prefix] == second[prefix]:
        prefix += 1
    return jaro + prefix * PREFIX_SCALE * (1 - jaro)


def token_jaccard(first: str, second: str) -> float:
    left, right = set(first.split()), set(second.split())
    union = left | right
    return len(left & right) / len(union) if union else 0.0


class _Record:
    def __init__(self, name: str, email: str) -> None:
        self.name = normalize_name(name)
        self.email = normalize_email(email)

    def blocking_keys(self) -> set[str]:
        keys = set()
        tokens = self.name.split()
        if tokens:
            keys.add("n:" + tokens[-1][:NAME_KEY_LENGTH])
        if self.email:
            keys.add("e:" + self.email)
        return keys


class _Clusters:
    """Union-find over record ids that also keeps the members of each root."""

    def __init__(self, ids: list[str]) -> None:
        self.parent = {i: i for i in ids}
        self.members = {i: [i] for i in ids}

    def find(self, item: str) -> str:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: str, second: str) -> None:
        a, b = self.find(first), self.find(second)
        if len(self.members[a]) < len(self.members[b]):
            a, b = b, a
        self.parent[b] = a
        self.members[a].extend(self.members.pop(b))

    def groups(self) -> list[list[str]]:
        return sorted(sorted(group) for group in self.members.values())


class EntityResolver:
    def __init__(self) -> None:
        self._records: dict[str, _Record] = {}
        self._scores: dict[tuple[str, str], float] = {}

    # Level 1
    def normalize_name(self, name: str) -> str:
        return normalize_name(name)

    def normalize_email(self, email: str) -> str:
        return normalize_email(email)

    def add_record(self, record_id: str, name: str, email: str) -> bool:
        if record_id in self._records:
            return False
        self._records[record_id] = _Record(name, email)
        return True

    def normalized(self, record_id: str) -> list[str]:
        record = self._records.get(record_id)
        return [record.name, record.email] if record else []

    def exact_groups(self) -> list[list[str]]:
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for record_id, record in self._records.items():
            if record.name or record.email:
                groups[(record.name, record.email)].append(record_id)
        return sorted(sorted(ids) for ids in groups.values() if len(ids) > 1)

    # Level 2
    def blocking_keys(self, record_id: str) -> list[str]:
        record = self._records.get(record_id)
        return sorted(record.blocking_keys()) if record else []

    def candidate_pairs(self) -> list[list[str]]:
        blocks: dict[str, list[str]] = defaultdict(list)
        for record_id in sorted(self._records):
            for key in self._records[record_id].blocking_keys():
                blocks[key].append(record_id)
        pairs = {pair for ids in blocks.values() for pair in combinations(ids, 2)}
        return [list(pair) for pair in sorted(pairs)]

    def jaro_winkler(self, first: str, second: str) -> float:
        return jaro_winkler(first, second)

    def token_jaccard(self, first: str, second: str) -> float:
        return token_jaccard(first, second)

    def similarity(self, first: str, second: str) -> float:
        if first not in self._records or second not in self._records:
            return 0.0
        low, high = sorted((first, second))
        if (low, high) not in self._scores:
            self._scores[(low, high)] = self._score(self._records[low], self._records[high])
        return self._scores[(low, high)]

    def is_match(self, first: str, second: str) -> bool:
        return (
            first in self._records
            and second in self._records
            and self.similarity(first, second) >= MATCH_THRESHOLD
        )

    def matches(self) -> list[list[str]]:
        return [pair for pair in self.candidate_pairs() if self.is_match(*pair)]

    # Level 3
    def components(self) -> list[list[str]]:
        clusters = _Clusters(list(self._records))
        for first, second in self.matches():
            if clusters.find(first) != clusters.find(second):
                clusters.union(first, second)
        return clusters.groups()

    def clusters(self) -> list[list[str]]:
        clusters = _Clusters(list(self._records))
        edges = sorted(self.matches(), key=lambda pair: (-self.similarity(*pair), *pair))
        for first, second in edges:
            root_a, root_b = clusters.find(first), clusters.find(second)
            if root_a != root_b and self._may_merge(clusters.members[root_a], clusters.members[root_b]):
                clusters.union(first, second)
        return clusters.groups()

    def canonical(self, record_id: str) -> str:
        group = self._entity_of(record_id)
        return min(group, key=self._canonical_order) if group else ""

    def aliases(self, record_id: str) -> list[str]:
        group = self._entity_of(record_id)
        if not group:
            return []
        keeper = self._records[self.canonical(record_id)].name
        return sorted({self._records[i].name for i in group} - {keeper, ""})

    # Level 4
    def pairwise_scores(self, predicted: list[list[str]], gold: list[list[str]]) -> list[float]:
        found, truth = _pairs(predicted), _pairs(gold)
        hits = len(found & truth)
        precision = hits / len(found) if found else 1.0
        recall = hits / len(truth) if truth else 1.0
        return [precision, recall, _harmonic(precision, recall)]

    def bcubed_scores(self, predicted: list[list[str]], gold: list[list[str]]) -> list[float]:
        guess = {i: set(group) for group in predicted for i in group}
        truth = {i: set(group) for group in gold for i in group}
        precision = sum(len(guess[i] & truth[i]) / len(guess[i]) for i in truth) / len(truth)
        recall = sum(len(guess[i] & truth[i]) / len(truth[i]) for i in truth) / len(truth)
        return [precision, recall, _harmonic(precision, recall)]

    def pair_errors(self, predicted: list[list[str]], gold: list[list[str]]) -> list[list[str]]:
        found, truth = _pairs(predicted), _pairs(gold)
        rows = [[FALSE_MERGE, *pair] for pair in found - truth]
        rows += [[MISSED, *pair] for pair in truth - found]
        return sorted(rows)

    # Helpers
    @staticmethod
    def _score(first: _Record, second: _Record) -> float:
        if first.email and first.email == second.email:
            return 1.0
        if not first.name or not second.name:
            return 0.0
        return JARO_WEIGHT * jaro_winkler(first.name, second.name) + JACCARD_WEIGHT * token_jaccard(
            first.name, second.name
        )

    def _may_merge(self, left: list[str], right: list[str]) -> bool:
        return all(self.similarity(a, b) >= MERGE_FLOOR for a in left for b in right)

    def _entity_of(self, record_id: str) -> list[str]:
        if record_id not in self._records:
            return []
        return next(group for group in self.clusters() if record_id in group)

    def _canonical_order(self, record_id: str) -> tuple[int, int, str]:
        record = self._records[record_id]
        filled = bool(record.name) + bool(record.email)
        return (-filled, -len(record.name), record_id)


def _pairs(groups: list[list[str]]) -> set[tuple[str, str]]:
    return {pair for group in groups for pair in combinations(sorted(group), 2)}


def _harmonic(precision: float, recall: float) -> float:
    total = precision + recall
    return 2 * precision * recall / total if total else 0.0
