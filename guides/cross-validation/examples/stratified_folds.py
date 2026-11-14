"""Three ways to cut 30 examples, 6 of them positive, into 3 folds.

The data arrives sorted, negatives first, as an export often does. A fold whose training part has
no positive at all cannot teach a classifier anything about them.
"""

import random

rng = random.Random(1)
labels = [0] * 24 + [1] * 6
K = 3


def shuffled(items) -> list:
    """A Fisher-Yates shuffle built on random(), whose sequence is stable across versions."""
    items = list(items)
    for i in range(len(items) - 1, 0, -1):
        j = int(rng.random() * (i + 1))
        items[i], items[j] = items[j], items[i]
    return items


def blocks(order: list[int]) -> list[list[int]]:
    size = len(order) // K
    return [order[f * size : (f + 1) * size] for f in range(K)]


def stratified(indexes: list[int]) -> list[list[int]]:
    folds: list[list[int]] = [[] for _ in range(K)]
    for label in (0, 1):
        members = shuffled(i for i in indexes if labels[i] == label)
        for position, index in enumerate(members):
            folds[position % K].append(index)  # deal each class round the folds
    return folds


everything = list(range(len(labels)))
for name, folds in [
    ("blocks as stored", blocks(everything)),
    ("blocks after a shuffle", blocks(shuffled(everything))),
    ("stratified", stratified(everything)),
]:
    held_out = [sum(labels[i] for i in fold) for fold in folds]
    to_learn = [6 - count for count in held_out]
    print(f"{name:24} positives held out {held_out}, left to learn from {to_learn}")
