from collections import defaultdict, deque

HOP_BASE = 16
RECENCY_BASE = 16
MAX_RECENCY_STEPS = 4
CHARACTERS_PER_TOKEN = 4

Fact = tuple[str, str, str]


class _Meta:
    __slots__ = ("time", "weight")

    def __init__(self, weight: int, time: int) -> None:
        self.weight = weight
        self.time = time


def fact_tokens(fact: Fact) -> int:
    """The characters of 'subject relation object', in groups of 4, rounded up."""
    characters = len(fact[0]) + len(fact[1]) + len(fact[2]) + 2
    return -(-characters // CHARACTERS_PER_TOKEN)


class GraphContext:
    def __init__(self) -> None:
        self._facts: dict[Fact, _Meta] = {}
        self._incident: dict[str, list[Fact]] = defaultdict(list)

    # Level 1
    def add_fact(self, subject: str, relation: str, obj: str, weight: int, time: int) -> bool:
        fact = (subject, relation, obj)
        if fact in self._facts:
            return False
        self._facts[fact] = _Meta(weight, time)
        self._incident[subject].append(fact)
        if obj != subject:
            self._incident[obj].append(fact)
        return True

    def size(self) -> int:
        return len(self._facts)

    def ego_network(self, entity: str, hops: int) -> list[list[str]]:
        return [[*fact, str(hop)] for hop, fact in self._within(entity, hops)]

    # Level 2
    def rank_facts(self, entity: str, hops: int, now: int, half_life: int) -> list[list[str]]:
        return [[*fact, str(hop), str(score)] for score, hop, fact in self._ranked(entity, hops, now, half_life)]

    # Level 3
    def build_context(
        self, entity: str, hops: int, now: int, half_life: int, budget: int
    ) -> list[list[str]]:
        return [
            [*fact, str(hop), str(score), str(tokens)]
            for score, hop, fact, tokens in self._packed(entity, hops, now, half_life, budget)
        ]

    # Level 4
    def explain(self, entity: str, subject: str, relation: str, obj: str) -> list[list[str]]:
        fact = (subject, relation, obj)
        if fact not in self._facts:
            return []
        return [list(step) for step in self._path(self._distances(entity), entity, fact)]

    def render_context(self, entity: str, hops: int, now: int, half_life: int, budget: int) -> str:
        chosen = self._packed(entity, hops, now, half_life, budget)
        used = sum(tokens for _, _, _, tokens in chosen)
        lines = [f"Context for {entity} ({len(chosen)} facts, {used} of {budget} tokens)"]
        distances = self._distances(entity)
        for number, (_, _, fact, _) in enumerate(chosen, start=1):
            path = self._path(distances, entity, fact)
            lines.append(f"[{number}] {' '.join(fact)} | path: {_path_text(entity, path)}")
        return "\n".join(lines)

    # Helpers
    def _distances(self, entity: str) -> dict[str, int]:
        distance = {entity: 0}
        queue = deque([entity])
        while queue:
            node = queue.popleft()
            for subject, _, obj in self._incident.get(node, ()):
                for other in (subject, obj):
                    if other not in distance:
                        distance[other] = distance[node] + 1
                        queue.append(other)
        return distance if entity in self._incident else {}

    def _within(self, entity: str, hops: int) -> list[tuple[int, Fact]]:
        distance = self._distances(entity)
        found = []
        for fact in self._facts:
            nearest = min(distance.get(fact[0], hops), distance.get(fact[2], hops))
            if nearest < hops:
                found.append((nearest + 1, fact))
        return sorted(found)

    def _score(self, hop: int, fact: Fact, now: int, half_life: int) -> int:
        meta = self._facts[fact]
        steps = min(MAX_RECENCY_STEPS, max(0, now - meta.time) // half_life)
        return meta.weight * (HOP_BASE >> (hop - 1)) * (RECENCY_BASE >> steps)

    def _ranked(
        self, entity: str, hops: int, now: int, half_life: int
    ) -> list[tuple[int, int, Fact]]:
        scored = [
            (self._score(hop, fact, now, half_life), hop, fact) for hop, fact in self._within(entity, hops)
        ]
        return sorted(scored, key=lambda item: (-item[0], item[1], item[2]))

    def _packed(
        self, entity: str, hops: int, now: int, half_life: int, budget: int
    ) -> list[tuple[int, int, Fact, int]]:
        remaining = budget
        chosen = []
        for score, hop, fact in self._ranked(entity, hops, now, half_life):
            tokens = fact_tokens(fact)
            if tokens <= remaining:
                chosen.append((score, hop, fact, tokens))
                remaining -= tokens
        return chosen

    def _parent(self, distances: dict[str, int], node: str) -> tuple[str, Fact]:
        """The nearest-to-the-entity step into `node`: the smallest neighbour one step closer, by
        the smallest fact between the two."""
        best: tuple[str, Fact] | None = None
        for fact in self._incident[node]:
            other = fact[2] if fact[0] == node else fact[0]
            if distances.get(other) == distances[node] - 1 and (
                best is None or (other, fact) < best
            ):
                best = (other, fact)
        assert best is not None
        return best

    def _path(self, distances: dict[str, int], entity: str, fact: Fact) -> list[Fact]:
        reachable = [node for node in (fact[0], fact[2]) if node in distances]
        if not reachable:
            return []
        near = min(reachable, key=lambda node: (distances[node], node))
        steps: list[Fact] = []
        node = near
        while node != entity:
            node, step = self._parent(distances, node)
            steps.append(step)
        steps.reverse()
        return [*steps, fact]


def _path_text(entity: str, path: list[Fact]) -> str:
    text = entity
    node = entity
    for subject, relation, obj in path:
        if node == subject:
            text += f" -{relation}-> {obj}"
            node = obj
        else:
            text += f" <-{relation}- {subject}"
            node = subject
    return text
