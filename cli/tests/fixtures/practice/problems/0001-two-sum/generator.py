import random


def generate(rng: random.Random, n: int) -> dict:
    size = max(n, 2)
    nums = [2 * value for value in rng.sample(range(-1000, 1000), size - 1)]
    odd = 2 * rng.randrange(-1000, 1000) + 1
    target = odd + rng.choice(nums)
    nums.insert(rng.randrange(size), odd)
    return {"nums": nums, "target": target}


def validate(case_input: dict) -> None:
    assert len(case_input["nums"]) >= 2, "at least two numbers"
