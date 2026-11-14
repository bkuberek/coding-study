"""Seeded equations and questions for evaluate-division.

`n` is the number of equations (capped at 1000); there are `n` questions too. Every variable
gets a hidden positive value from a small set, and each equation `a / b` uses the exact ratio
of the hidden values, so the equations are consistent by construction and every quotient lies
between 1/12 and 12. Equations first build a random forest over the variables (a few groups,
some of them long chains), then the rest add consistent cycles and repeats. Questions mix
linked pairs, pairs from different groups, a variable over itself, and unknown names.
"""

import random
import string

MAX_EQUATIONS = 1000
HIDDEN_VALUES = [1, 2, 3, 4, 5, 6, 8, 10, 12]
ALPHABET = string.ascii_lowercase + string.digits


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_EQUATIONS)
    names = _names(rng, max(2, count * 3 // 4 + 1) + 3)
    unknown, names = names[:3], names[3:]
    hidden = {name: rng.choice(HIDDEN_VALUES) for name in names}
    pairs: list[tuple[str, str]] = []
    for index in range(1, len(names)):
        if len(pairs) == count:
            break
        if rng.random() < 0.9:
            parent = names[rng.randint(max(0, index - 3), index - 1)]
            pairs.append((names[index], parent) if rng.random() < 0.5 else (parent, names[index]))
    while len(pairs) < count:
        a, b = rng.sample(names, 2)
        pairs.append((a, b))
    rng.shuffle(pairs)
    equations = [[a, b] for a, b in pairs]
    values = [hidden[a] / hidden[b] for a, b in pairs]
    used = sorted({name for pair in pairs for name in pair})
    queries = []
    for _ in range(count):
        kind = rng.random()
        if kind < 0.1:
            name = rng.choice(used)
            queries.append([name, name])
        elif kind < 0.2:
            queries.append([rng.choice(used + unknown), rng.choice(unknown)])
        else:
            queries.append(rng.sample(used, 2) if len(used) >= 2 else [used[0], used[0]])
    return {"equations": equations, "values": values, "queries": queries}


def _names(rng: random.Random, count: int) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    while len(names) < count:
        name = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(1, 5)))
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def validate(case_input: dict) -> None:
    equations, values, queries = case_input["equations"], case_input["values"], case_input["queries"]
    assert 1 <= len(equations) <= MAX_EQUATIONS and len(values) == len(equations), "bad equation count"
    assert 1 <= len(queries) <= MAX_EQUATIONS, "bad query count"
    for pair in equations + queries:
        assert len(pair) == 2, "pairs have two names"
        for name in pair:
            assert 1 <= len(name) <= 5 and all(ch in ALPHABET for ch in name), "bad name"
    assert all(a != b for a, b in equations), "an equation repeats its variable"
    assert all(0.05 <= value <= 20.0 for value in values), "value out of range"
