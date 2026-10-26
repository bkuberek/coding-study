"""Seeded inputs for {{title}} (docs/specs/problem-format.md#generated-cases-and-generatorpy).

Trees are level-order lists with `None` for missing children and trailing `None`s trimmed
(problem-format.md#treenode). This one builds complete trees; TODO: vary the shapes.
"""

import random
from typing import Any

MAX_NODES = 10**4
VALUE_LIMIT = 10**4


def generate(rng: random.Random, n: int) -> dict[str, Any]:
    size = min(n, MAX_NODES)
    return {"root": [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(size)]}


def validate(case_input: dict[str, Any]) -> None:
    root: list[int | None] = case_input["root"]
    nodes = [value for value in root if value is not None]
    assert len(nodes) <= MAX_NODES, "too many nodes"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nodes), "value out of range"
    assert not root or root[-1] is not None, "trailing nulls must be trimmed"
