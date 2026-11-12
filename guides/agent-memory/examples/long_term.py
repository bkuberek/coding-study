"""Retrieving long-term memories by recency, importance and relevance, each scaled to [0, 1] and added.

The weights, the scaling and the hourly decay of 0.995 follow the design of Park and colleagues'
generative agents. The embedding model is a fake: known words map to five named axes.
"""

import math

AXES = ("food", "health", "family", "weather", "shopping")
WORD_AXIS = {
    "cook": "food", "dinner": "food", "recipes": "food", "vegan": "food", "list": "shopping",
    "shopping": "shopping", "allergic": "health", "peanuts": "health", "sister": "family",
    "bea": "family", "weather": "weather", "nice": "weather",
}
MEMORIES = [  # (hours since last used, importance from 1 to 10, text)
    (1, 2, "Ana asked for a shopping list for Friday"),
    (30, 9, "Ana is allergic to peanuts"),
    (5, 3, "Ana prefers recipes under 30 minutes"),
    (200, 8, "Ana's sister Bea is vegan"),
    (2, 1, "Ana said the weather is nice"),
]


def embed(text: str) -> list[float]:
    counts = [0.0] * len(AXES)
    for word in text.lower().replace("?", "").replace("'s", "").split():
        if word in WORD_AXIS:
            counts[AXES.index(WORD_AXIS[word])] += 1
    length = math.sqrt(sum(c * c for c in counts))
    return [c / length for c in counts] if length else counts


def min_max(values: list[float]) -> list[float]:
    low, high = min(values), max(values)
    return [(v - low) / (high - low) if high > low else 0.0 for v in values]


def retrieve(query: str, k: int = 3) -> list[tuple[float, str]]:
    q = embed(query)
    recency = min_max([0.995**hours for hours, _, _ in MEMORIES])
    importance = min_max([float(score) for _, score, _ in MEMORIES])
    relevance = min_max([sum(a * b for a, b in zip(q, embed(text))) for _, _, text in MEMORIES])
    for (_, _, text), r, i, v in zip(MEMORIES, recency, importance, relevance):
        print(f"    {text:<40} recency {r:.2f}  importance {i:.2f}  relevance {v:.2f}  sum {r + i + v:.2f}")
    scored = [(r + i + v, text) for (_, _, text), r, i, v in zip(MEMORIES, recency, importance, relevance)]
    return sorted(scored, key=lambda pair: -pair[0])[:k]


query = "What can I cook for dinner with my sister Bea?"
print(f"query: {query}")
best = retrieve(query)
print("top 3:", [text for _, text in best])
by_relevance = sorted(MEMORIES, key=lambda m: -sum(a * b for a, b in zip(embed(query), embed(m[2]))))
print("top 3 by relevance alone:", [text for _, _, text in by_relevance[:3]])
