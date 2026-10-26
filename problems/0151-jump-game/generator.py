"""Seeded inputs for jump-game.

`n` is the array length, clamped to 1..10^4. Each input picks one shape:

- wall: an index `p` before the end gets 0 and every earlier index jumps at most up to `p`, so
  the end is unreachable; earlier jumps are large, which makes marking every target quadratic;
- open: every value is at least 1, so the end is always reachable;
- mixed: small values with frequent zeros, where the answer depends on the draw.

From LONG_JUMPS_FROM values on (the bench ladder), every input is long jumps instead: values
between n / 2 and n, so the end is always reachable, the scans from the front and from the
back both pass every index, and marking every target costs about 3 n^2 / 8 steps. A wall
would stop the forward scan at a position that varies from seed to seed.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**4
MAX_JUMP = 10**5
SMALL_JUMP = 3
LONG_JUMPS_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length >= LONG_JUMPS_FROM:
        return {"nums": [rng.randint(length // 2, length) for _ in range(length)]}
    shape = rng.choice(("wall", "open", "mixed")) if length > 1 else "open"
    if shape == "open":
        top = rng.choice((SMALL_JUMP, length, MAX_JUMP))
        return {"nums": [rng.randint(1, top) for _ in range(length)]}
    if shape == "mixed":
        return {"nums": [rng.randint(0, SMALL_JUMP) for _ in range(length)]}
    wall = rng.randint(0, length - 2)
    nums = [rng.randint(0, wall - i) for i in range(wall)]
    nums.append(0)
    nums += [rng.randint(0, MAX_JUMP) for _ in range(length - wall - 1)]
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(0 <= jump <= MAX_JUMP for jump in nums), "jump out of range"
