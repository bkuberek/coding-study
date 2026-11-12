"""Search by meaning and by words over the same documents, then fuse the two rankings.

The embedding model is a fake: a table of word vectors over four made-up axes of meaning
(money, travel, food, software). A text's embedding is the average of its known words' vectors,
scaled to length 1. A real model learns thousands of axes nobody names, but the geometry is the same.
"""

import math

AXES = ("money", "travel", "food", "software")
WORD_VECTORS = {
    "refund": (0.9, 0.1, 0.0, 0.1), "payment": (0.9, 0.0, 0.0, 0.2), "money": (1.0, 0.0, 0.0, 0.0),
    "charge": (0.8, 0.0, 0.0, 0.2), "purchase": (0.8, 0.1, 0.1, 0.0), "back": (0.3, 0.2, 0.0, 0.0),
    "flight": (0.1, 1.0, 0.0, 0.0), "hotel": (0.2, 0.9, 0.1, 0.0), "trip": (0.1, 0.9, 0.1, 0.0),
    "recipe": (0.0, 0.0, 1.0, 0.0), "dinner": (0.1, 0.1, 0.9, 0.0), "spicy": (0.0, 0.0, 0.8, 0.0),
    "error": (0.0, 0.0, 0.0, 1.0), "login": (0.1, 0.0, 0.0, 0.9), "app": (0.1, 0.1, 0.0, 0.9),
}
DOCUMENTS = [
    "how to get your money back for a purchase",
    "booking a hotel near the airport before a flight",
    "a spicy recipe for a quick dinner",
    "the app shows error ERR-4012 at login",
    "change the card used for each payment",
    "plan a trip on a budget",
]


def words(text: str) -> list[str]:
    return text.lower().split()


def normalize(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(x * x for x in vector))
    return [x / length for x in vector] if length else vector


def embed(text: str) -> list[float]:
    known = [WORD_VECTORS[word] for word in words(text) if word in WORD_VECTORS]
    if not known:
        return [0.0] * len(AXES)
    return normalize([sum(column) / len(known) for column in zip(*known)])


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def cosine(a: list[float], b: list[float]) -> float:
    lengths = math.sqrt(dot(a, a)) * math.sqrt(dot(b, b))
    return dot(a, b) / lengths if lengths else 0.0


INDEX = [embed(document) for document in DOCUMENTS]  # computed once, when documents are added


def by_meaning(query: str) -> list[int]:
    q = embed(query)
    if not any(q):
        return []  # a zero vector has no direction, so nothing can be compared with it
    # Every stored vector has length 1, so the dot product is the cosine similarity.
    scores = {i: dot(q, vector) for i, vector in enumerate(INDEX) if any(vector)}
    return sorted(scores, key=lambda i: (-scores[i], i))


def by_words(query: str) -> list[int]:
    wanted = set(words(query))
    shared = {i: len(wanted & set(words(document))) for i, document in enumerate(DOCUMENTS)}
    return [i for i in sorted(shared, key=lambda i: (-shared[i], i)) if shared[i] > 0]


def fuse(*rankings: list[int], k: int = 60) -> list[int]:
    """Reciprocal rank fusion: each ranking gives a document 1 / (k + its rank)."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, i in enumerate(ranking, start=1):
            scores[i] = scores.get(i, 0.0) + 1 / (k + rank)
    return sorted(scores, key=lambda i: (-scores[i], i))


for i, document in enumerate(DOCUMENTS):
    print(f"{i}: {document}")
a, b = embed("refund payment"), embed("money back for a purchase")
print(f"cosine {cosine(a, b):.3f}, dot of the unit vectors {dot(a, b):.3f}, length {math.sqrt(dot(a, a)):.3f}")
for query in ["refund", "refund my payment", "ERR-4012", "login error"]:
    meaning, matching = by_meaning(query), by_words(query)
    print(f"{query!r}: by meaning {meaning[:3]}, by words {matching[:3]}, fused {fuse(meaning, matching)[:3]}")
