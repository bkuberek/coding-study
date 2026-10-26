import random


def generate(rng: random.Random, n: int) -> dict:
    return {"nums": [rng.randrange(-1000, 1000) for _ in range(max(n, 1))]}


def validate(case_input: dict) -> None:
    assert case_input["nums"], "at least one number"
